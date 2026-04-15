from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass(slots=True)
class ComposeProjectPaths:
    container_id: int
    host_name: str

    @property
    def project_name(self) -> str:
        host_name_safe = self.host_name.replace(" ", "_").lower()
        return f"bicep_cids_{self.container_id}_{host_name_safe}"

    @property
    def work_dir(self) -> str:
        return f"/tmp/{self.project_name}"

    @property
    def compose_file_path(self) -> str:
        return os.path.join(self.work_dir, "docker-compose.yaml")


@dataclass(slots=True)
class PreparedComposeHostDeployment:
    host_system: Any
    services: list[Any]
    compose_data: dict[str, Any]
    runtime_config_files: dict[str, Any]
    paths: ComposeProjectPaths


class ComposeSpecManager:
    def __init__(self, get_config_by_id, get_core_url):
        self._get_config_by_id = get_config_by_id
        self._get_core_url = get_core_url

    def build_paths(self, container_id: int, host_name: str) -> ComposeProjectPaths:
        return ComposeProjectPaths(container_id=container_id, host_name=host_name)

    def load_compose_data(self, raw_content) -> dict[str, Any]:
        return yaml.safe_load(raw_content)

    def group_services_by_host(
        self, compose_data, cids_configurations, default_host_id
    ) -> dict[int, list[Any]]:
        services_by_host = defaultdict(list)

        if cids_configurations:
            # cids_configurations can be a list of CidsServiceConfig (setup) or IdsComponent (update)
            for svc_conf in cids_configurations:
                host_id = getattr(svc_conf, 'host_system_id', None)
                if host_id is None:
                    # Handle IdsComponent which might have it differently or CidsServiceConfig
                    host_id = default_host_id
                
                service_name = getattr(svc_conf, 'service_name', None) or getattr(svc_conf, 'name', None)
                if not service_name and hasattr(svc_conf, 'name'):
                    pass
                
                services_by_host[host_id].append(svc_conf)
        elif "services" in compose_data:
            for svc_name in compose_data["services"]:
                services_by_host[default_host_id].append(
                    type("obj", (object,), {"service_name": svc_name, "count": 1})
                )

        return services_by_host

    async def resolve_service_runtime_configs(
        self, db_session, compose_data, cids_configurations
    ) -> dict[str, Any]:
        service_runtime_configs = {}

        for svc_conf in cids_configurations:
            service_name = getattr(svc_conf, 'service_name', None)
            if not service_name and hasattr(svc_conf, 'role'):
                pass

            if not service_name:
                continue

            svc_data = compose_data.get("services", {}).get(service_name)
            if svc_data is None:
                continue # Might be a component not in this compose file

            config_id = getattr(svc_conf, 'runtime_configuration_id', None)
            if not config_id:
                continue

            labels = svc_data.get("labels", {})
            mount_path, _ = self._parse_bicep_labels(labels)
            if not mount_path:
                raise ValueError(
                    f"Service '{service_name}' requires a "
                    "bicep.config.mount label for runtime configurations."
                )

            expected_extension = self._get_file_extension(mount_path)
            runtime_config = await self._get_config_by_id(
                db_session, config_id
            )
            if runtime_config is None:
                continue

            runtime_config_path = (
                getattr(runtime_config, "file_path", None)
                or getattr(runtime_config, "name", None)
            )
            actual_extension = self._get_file_extension(runtime_config_path)
            if not self._extensions_are_compatible(
                expected_extension,
                actual_extension,
            ):
                raise ValueError(
                    f"Service '{service_name}' expects a config ending in "
                    f"'{expected_extension}' but got '{actual_extension}'."
                )

            service_runtime_configs[service_name] = runtime_config

        return service_runtime_configs

    def prepare_host_deployment(
        self,
        compose_data,
        services,
        ids_container,
        host_system,
        service_runtime_configs,
    ) -> PreparedComposeHostDeployment | None:
        host_compose_data = self._build_host_compose_data(compose_data, services)
        if not host_compose_data["services"]:
            return None

        paths = self.build_paths(ids_container.id, host_system.name)
        os.makedirs(paths.work_dir, exist_ok=True)
        runtime_config_files = self._apply_service_customizations(
            host_compose_data,
            paths.work_dir,
            ids_container.port,
            service_runtime_configs,
        )

        return PreparedComposeHostDeployment(
            host_system=host_system,
            services=list(services),
            compose_data=host_compose_data,
            runtime_config_files=runtime_config_files,
            paths=paths,
        )

    async def write_deployment_files(self, deployment, ruleset) -> None:
        with open(deployment.paths.compose_file_path, "w") as handle:
            yaml.dump(deployment.compose_data, handle)

        if ruleset:
            ruleset_content = await ruleset.read_content()
            with open(os.path.join(deployment.paths.work_dir, "rules.yaml"), "wb") as handle:
                handle.write(ruleset_content)

        for host_path, runtime_config in deployment.runtime_config_files.items():
            content = await runtime_config.read_content()
            with open(host_path, "wb") as handle:
                if isinstance(content, str):
                    handle.write(content.encode("utf-8"))
                else:
                    handle.write(content)

    def _build_host_compose_data(self, compose_data, services) -> dict[str, Any]:
        host_compose_data = compose_data.copy()
        host_compose_data["services"] = {}

        for svc in services:
            service_name = getattr(svc, 'service_name', None)
            if service_name and service_name in compose_data["services"]:
                svc_data = compose_data["services"][service_name].copy()
                svc_data.pop("profiles", None)
                svc_data.pop("container_name", None)
                
                # Apply scaling
                count = getattr(svc, 'count', 1)
                if count > 1:
                    svc_data["deploy"] = {"replicas": count}
                
                host_compose_data["services"][service_name] = svc_data

        return host_compose_data

    def _apply_service_customizations(
        self, host_compose_data, work_dir, container_port, service_runtime_configs
    ) -> dict[str, Any]:
        runtime_config_files = {}

        for svc_name, svc_data in host_compose_data["services"].items():
            labels = svc_data.get("labels", {})
            mount_path, is_sensor = self._parse_bicep_labels(labels)
            runtime_config = service_runtime_configs.get(svc_name)

            if mount_path and runtime_config:
                host_path = self._build_runtime_config_host_path(
                    work_dir, svc_name, runtime_config
                )
                runtime_config_files[host_path] = runtime_config
                self._inject_config_mount(svc_data, host_path, mount_path)

            if is_sensor:
                self._inject_sensor_settings(svc_data, container_port)

        return runtime_config_files

    def _parse_bicep_labels(self, labels) -> tuple[str | None, bool]:
        mount_path = None
        is_sensor = False

        if isinstance(labels, dict):
            mount_path = labels.get("bicep.config.mount")
            is_sensor = labels.get("bicep.sensor") in ("true", True, "1")
        elif isinstance(labels, list):
            for label in labels:
                if label.startswith("bicep.config.mount="):
                    mount_path = label.split("=", 1)[1]
                elif label.startswith("bicep.sensor="):
                    is_sensor = label.split("=", 1)[1].lower() in ("true", "1")

        return mount_path, is_sensor

    def _get_file_extension(self, path: str | None) -> str | None:
        if not path:
            return None
        extension = os.path.splitext(path)[1].lower()
        return extension or None

    def _extensions_are_compatible(
        self, expected: str | None, actual: str | None
    ) -> bool:
        if not expected or not actual:
            return True
        aliases = {
            ".yaml": {".yaml", ".yml"},
            ".yml": {".yaml", ".yml"},
        }
        return actual in aliases.get(expected, {expected})

    def _build_runtime_config_host_path(
        self, work_dir, service_name, runtime_config
    ) -> str:
        extension = self._get_file_extension(runtime_config.file_path) or ".conf"
        safe_service_name = service_name.replace("/", "_").replace(" ", "_")
        return os.path.join(work_dir, f"{safe_service_name}{extension}")

    def _inject_config_mount(self, svc_data, source_path, mount_path) -> None:
        volume_entry = f"{source_path}:{mount_path}"

        if "volumes" not in svc_data:
            svc_data["volumes"] = []

        svc_data["volumes"] = [
            volume
            for volume in svc_data["volumes"]
            if not (
                isinstance(volume, str) and volume.endswith(f":{mount_path}")
            )
        ]
        svc_data["volumes"].append(volume_entry)

    def _ensure_env_dict(self, svc_data) -> None:
        if "environment" not in svc_data:
            svc_data["environment"] = {}
        elif isinstance(svc_data["environment"], list):
            env_dict = {}
            for entry in svc_data["environment"]:
                key, _, value = entry.partition("=")
                env_dict[key] = value
            svc_data["environment"] = env_dict

    def _inject_sensor_settings(self, svc_data, container_port) -> None:
        self._ensure_env_dict(svc_data)
        svc_data["environment"]["PORT"] = str(container_port)
        svc_data["environment"].setdefault("CORE_URL", self._get_core_url())
        svc_data["environment"].setdefault("TZ", "UTC")
