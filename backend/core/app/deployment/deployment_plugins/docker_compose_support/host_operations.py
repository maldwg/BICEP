from __future__ import annotations

import asyncio
import io
import os
import shutil
import tarfile
from collections import defaultdict

from python_on_whales.exceptions import DockerException


class ComposeHostOperations:
    def __init__(
        self,
        docker_client_cls,
        docker_sdk_module,
        ids_component_cls,
        logger,
        get_core_url,
    ):
        self._docker_client_cls = docker_client_cls
        self._docker_sdk = docker_sdk_module
        self._ids_component_cls = ids_component_cls
        self._logger = logger
        self._get_core_url = get_core_url

    def get_docker_host_url(self, host_system) -> str:
        host_ip, docker_port = host_system.get_host_and_docker_port()
        return f"tcp://{host_ip}:{docker_port}"

    def group_components_by_host(self, components) -> dict[int, list]:
        components_by_host = defaultdict(list)
        for component in components:
            components_by_host[component.host_system_id].append(component)
        return components_by_host

    async def copy_runtime_configs(self, deployment) -> None:
        await asyncio.to_thread(self._copy_runtime_configs_blocking, deployment)

    async def start_project(
        self, deployment, ids_container, db_session, env_vars=None
    ) -> None:
        docker_host_url = self.get_docker_host_url(deployment.host_system)

        try:
            client = self._docker_client_cls(
                host=docker_host_url,
                compose_files=[deployment.paths.compose_file_path],
                compose_project_name=deployment.paths.project_name,
            )

            env = os.environ.copy()
            env["CORE_URL"] = self._get_core_url()
            if env_vars:
                env.update(env_vars)
            os.environ.update(env)

            await asyncio.to_thread(
                lambda: client.compose.up(
                    detach=True,
                    quiet=False,
                    scales=self._build_scale_config(deployment.services),
                )
            )

            self._register_components(client, ids_container, deployment.host_system, db_session)
        except DockerException as exc:
            raise Exception(
                f"Docker Compose failed on {deployment.host_system.name}: {exc}"
            )

    async def teardown_project(self, host_system, components, paths) -> None:
        await asyncio.to_thread(
            self._teardown_remote_project_blocking,
            host_system,
            components,
            paths,
        )
        await self._remove_local_work_dir(paths.work_dir)

    def _cleanup_compose_resources_blocking(self, docker_host_url, project_name) -> None:
        client = self._docker_sdk.DockerClient(base_url=docker_host_url)
        label_filter = {"label": [f"com.docker.compose.project={project_name}"]}
        try:
            for container in client.containers.list(all=True, filters=label_filter):
                try:
                    container.remove(force=True)
                except Exception:
                    pass

            for network in client.networks.list(filters=label_filter):
                try:
                    network.remove()
                except Exception:
                    pass

            for volume in client.volumes.list(filters=label_filter):
                try:
                    volume.remove(force=True)
                except Exception:
                    pass
        finally:
            client.close()

    def _remove_remote_work_dir_blocking(self, docker_host_url, work_dir) -> None:
        if not work_dir.startswith("/tmp/bicep_cids_"):
            return

        host_docker = self._docker_sdk.DockerClient(base_url=docker_host_url)
        cleanup_container = None
        try:
            cleanup_container = host_docker.containers.create(
                "alpine",
                ["rm", "-rf", work_dir],
                volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
            )
            cleanup_container.start()
            cleanup_container.wait()
        except Exception as exc:
            self._logger.warning(
                f"Failed to remove remote work dir {work_dir}: {exc}"
            )
        finally:
            if cleanup_container is not None:
                try:
                    cleanup_container.remove(force=True)
                except Exception:
                    pass
            host_docker.close()

    async def _remove_local_work_dir(self, work_dir) -> None:
        if os.path.exists(work_dir):
            await asyncio.to_thread(shutil.rmtree, work_dir, True)

    def _copy_runtime_configs_blocking(self, deployment) -> None:
        host_docker = self._docker_sdk.DockerClient(
            base_url=self.get_docker_host_url(deployment.host_system)
        )
        tmp_container = None
        try:
            tmp_container = host_docker.containers.create(
                "alpine",
                "true",
                volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
            )
            tmp_container.start()
            tmp_container.wait()
            tmp_container.remove()

            tmp_container = host_docker.containers.create(
                "alpine",
                ["mkdir", "-p", deployment.paths.work_dir],
                volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
            )
            tmp_container.start()
            tmp_container.wait()

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                for host_path in deployment.runtime_config_files:
                    local_name = os.path.basename(host_path)
                    tar.add(host_path, arcname=local_name)
            tar_stream.seek(0)

            tmp_container.put_archive(deployment.paths.work_dir, tar_stream)
        finally:
            if tmp_container is not None:
                try:
                    tmp_container.remove(force=True)
                except Exception:
                    pass
            host_docker.close()

    def _teardown_remote_project_blocking(self, host_system, components, paths) -> None:
        docker_host_url = self.get_docker_host_url(host_system)

        try:
            client = self._docker_client_cls(
                host=docker_host_url,
                compose_project_name=paths.project_name,
            )
            try:
                client.compose.down(volumes=True, timeout=15)
            except DockerException:
                docker_client = self._docker_sdk.DockerClient(base_url=docker_host_url)
                try:
                    for component in components:
                        try:
                            container = docker_client.containers.get(component.name)
                            container.stop(timeout=10)
                            container.remove()
                        except self._docker_sdk.errors.NotFound:
                            continue
                finally:
                    docker_client.close()

            self._cleanup_compose_resources_blocking(
                docker_host_url, paths.project_name
            )
        except Exception as exc:
            self._logger.error(f"Teardown error on {host_system.name}: {exc}")
        finally:
            self._remove_remote_work_dir_blocking(docker_host_url, paths.work_dir)

    def _build_scale_config(self, services) -> dict[str, int]:
        scales = {}
        for svc in services:
            count = getattr(svc, "count", 1) or 1
            if count > 1:
                scales[svc.service_name] = count
        return scales

    def _register_components(self, client, ids_container, host_system, db_session) -> None:
        containers = client.compose.ps()

        for container in containers:
            exposed_port = self._extract_exposed_port(container)

            labels = getattr(container.config, "labels", None) or getattr(
                container, "labels", {}
            ) or {}
            role_label = labels.get("bicep.role")

            if role_label and role_label.upper() in ["INFRA", "SENSOR", "PIPELINE"]:
                role = role_label.upper()
            else:
                role = (
                    "AGGREGATOR"
                    if "aggregator" in container.name.lower()
                    else "SENSOR"
                )

            if role == "SENSOR":
                exposed_port = ids_container.port

            component = self._ids_component_cls(
                ids_id=ids_container.id,
                name=container.name,
                role=role,
                port=exposed_port,
                host_system_id=host_system.id,
            )
            db_session.add(component)
            if (
                hasattr(ids_container, "components")
                and ids_container.components is not None
            ):
                ids_container.components.append(component)

    def _extract_exposed_port(self, container):
        ports = container.network_settings.ports
        if ports:
            for bindings in ports.values():
                if bindings and len(bindings) > 0:
                    return int(bindings[0]["HostPort"])
        return None
