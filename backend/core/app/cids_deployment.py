import asyncio
import io
import os
import tarfile
from collections import defaultdict

import docker
import yaml
from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException

from app.logger import LOGGER
from app.models.configuration import get_config_by_id
from app.models.docker_host_system import get_host_by_id
from app.models.ids_component import IdsComponent
from app.utils import get_core_url


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def start_cids_deployment(
    ids_container,
    ids_tool,
    config,
    ruleset,
    db_session,
    cids_configurations=None,
    env_vars=None,
):
    """
    Deploys a CIDS using the implementation registered for its deployment type.
    """
    if ids_tool.deployment_type == "DOCKER_COMPOSE":
        await deploy_docker_compose(
            ids_container,
            ids_tool,
            config,
            ruleset,
            db_session,
            cids_configurations,
            env_vars=env_vars,
        )
    else:
        raise ValueError(f"Unsupported deployment type: {ids_tool.deployment_type}")


# ---------------------------------------------------------------------------
# Docker Compose deployment (orchestrator)
# ---------------------------------------------------------------------------


async def deploy_docker_compose(
    ids_container,
    ids_tool,
    config,
    ruleset,
    db_session,
    cids_configurations,
    env_vars=None,
):
    """Orchestrates a full Docker Compose CIDS deployment."""

    compose_data = yaml.safe_load(await config.read_content())
    LOGGER.debug(f"CIDS_CONFIG: {cids_configurations}")
    service_runtime_configs = await _resolve_service_runtime_configs(
        db_session, compose_data, cids_configurations or []
    )

    default_host_id = ids_container.host_system.id
    services_by_host = _group_services_by_host(
        compose_data, cids_configurations, default_host_id
    )

    for host_id, services in services_by_host.items():
        host_system = await get_host_by_id(db_session, host_id)
        host_compose_data = _build_host_compose_data(compose_data, services)

        if not host_compose_data["services"]:
            continue

        work_dir = _prepare_work_dir(ids_container.id, host_system.name)
        runtime_config_files = _apply_service_customizations(
            host_compose_data,
            work_dir,
            ids_container.port,
            service_runtime_configs,
        )

        await _write_deployment_files(
            work_dir, host_compose_data, ruleset, runtime_config_files
        )

        docker_host_url = _get_docker_host_url(host_system)

        if runtime_config_files:
            await _copy_config_files_to_remote_host(
                docker_host_url, work_dir, runtime_config_files
            )

        await _run_compose_and_register(
            docker_host_url,
            work_dir,
            ids_container,
            host_system,
            services,
            db_session,
            env_vars,
        )

    await db_session.commit()


# ---------------------------------------------------------------------------
# Service grouping & compose data filtering
# ---------------------------------------------------------------------------


def _group_services_by_host(compose_data, cids_configurations, default_host_id):
    """Build a ``{host_id: [services]}`` mapping."""
    services_by_host = defaultdict(list)

    if cids_configurations:
        for svc_conf in cids_configurations:
            services_by_host[svc_conf.host_system_id].append(svc_conf)
    elif "services" in compose_data:
        for svc_name in compose_data["services"]:
            services_by_host[default_host_id].append(
                type("obj", (object,), {"service_name": svc_name, "count": 1})
            )

    return services_by_host


def _build_host_compose_data(compose_data, services):
    """Filter compose services for a specific host, stripping BICEP-managed keys."""
    host_compose_data = compose_data.copy()
    host_compose_data["services"] = {}

    for svc in services:
        if svc.service_name in compose_data["services"]:
            svc_data = compose_data["services"][svc.service_name].copy()
            # Remove profiles — BICEP explicitly selects services to deploy
            svc_data.pop("profiles", None)
            # Remove container_name — let Docker Compose use project-name prefix
            # to avoid conflicts when multiple CIDS use the same compose file
            svc_data.pop("container_name", None)
            host_compose_data["services"][svc.service_name] = svc_data

    return host_compose_data


# ---------------------------------------------------------------------------
# Label parsing & per-service customizations
# ---------------------------------------------------------------------------


def _parse_bicep_labels(labels):
    """Extract ``bicep.config.mount`` and ``bicep.sensor`` from service labels.

    Handles both dict and list label formats used by Docker Compose.
    """
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


def _get_file_extension(path: str | None) -> str | None:
    if not path:
        return None
    extension = os.path.splitext(path)[1].lower()
    return extension or None


def _extensions_are_compatible(expected: str | None, actual: str | None) -> bool:
    if not expected or not actual:
        return True
    aliases = {
        ".yaml": {".yaml", ".yml"},
        ".yml": {".yaml", ".yml"},
    }
    return actual in aliases.get(expected, {expected})


async def _resolve_service_runtime_configs(db_session, compose_data, cids_configurations):
    service_runtime_configs = {}

    for svc_conf in cids_configurations:
        service_name = svc_conf.service_name
        svc_data = compose_data.get("services", {}).get(service_name)
        if svc_data is None:
            raise ValueError(f"Service '{service_name}' not found in deployment config.")

        labels = svc_data.get("labels", {})
        mount_path, _ = _parse_bicep_labels(labels)
        expected_extension = _get_file_extension(mount_path)

        if not svc_conf.runtime_configuration_id:
            continue

        runtime_config = await get_config_by_id(db_session, svc_conf.runtime_configuration_id)
        if runtime_config is None:
            raise ValueError(
                f"Runtime configuration {svc_conf.runtime_configuration_id} for service '{service_name}' was not found."
            )

        if not mount_path:
            raise ValueError(
                f"Service '{service_name}' does not declare a bicep.config.mount label, so no runtime config can be injected."
            )

        actual_extension = _get_file_extension(runtime_config.file_path)
        if not _extensions_are_compatible(expected_extension, actual_extension):
            raise ValueError(
                f"Service '{service_name}' expects a config ending in '{expected_extension}', "
                f"but '{runtime_config.name}' ends in '{actual_extension}'."
            )

        service_runtime_configs[service_name] = runtime_config

    return service_runtime_configs


def _build_runtime_config_host_path(work_dir, service_name, runtime_config):
    extension = _get_file_extension(runtime_config.file_path) or ".conf"
    safe_service_name = service_name.replace("/", "_").replace(" ", "_")
    return os.path.join(work_dir, f"{safe_service_name}{extension}")


def _inject_config_mount(svc_data, source_path, mount_path):
    """Add a volume mount for the BICEP runtime config file."""
    volume_entry = f"{source_path}:{mount_path}"

    if "volumes" not in svc_data:
        svc_data["volumes"] = []

    # Remove any existing mount to the same container path
    svc_data["volumes"] = [
        v
        for v in svc_data["volumes"]
        if not (isinstance(v, str) and v.endswith(f":{mount_path}"))
    ]
    svc_data["volumes"].append(volume_entry)


def _ensure_env_dict(svc_data):
    """Ensure ``svc_data["environment"]`` is a dict (convert list format if needed)."""
    if "environment" not in svc_data:
        svc_data["environment"] = {}
    elif isinstance(svc_data["environment"], list):
        env_dict = {}
        for entry in svc_data["environment"]:
            k, _, v = entry.partition("=")
            env_dict[k] = v
        svc_data["environment"] = env_dict


def _inject_sensor_settings(svc_data, container_port):
    """Add env vars (PORT, CORE_URL, TZ) for a sensor service.

    The sensor runs with ``network_mode: host``, so Docker port mappings are
    unnecessary — the FastAPI plugin binds directly on the host network using
    the PORT environment variable.
    """
    # Inject environment variables (mirrors single-container IDS in docker.py)
    _ensure_env_dict(svc_data)
    svc_data["environment"]["PORT"] = str(container_port)
    svc_data["environment"].setdefault("CORE_URL", get_core_url())
    svc_data["environment"].setdefault("TZ", "UTC")


def _apply_service_customizations(
    host_compose_data, work_dir, container_port, service_runtime_configs
):
    """Walk services, inject config mounts and sensor settings based on labels.

    Returns a ``{host_path: Configuration}`` map for selected runtime configs.
    """
    runtime_config_files = {}

    for svc_name, svc_data in host_compose_data["services"].items():
        labels = svc_data.get("labels", {})
        mount_path, is_sensor = _parse_bicep_labels(labels)
        runtime_config = service_runtime_configs.get(svc_name)

        if mount_path and runtime_config:
            host_path = _build_runtime_config_host_path(
                work_dir, svc_name, runtime_config
            )
            runtime_config_files[host_path] = runtime_config
            _inject_config_mount(svc_data, host_path, mount_path)
            LOGGER.info(f"Will mount config into {svc_name} at {mount_path}")

        if is_sensor:
            LOGGER.info(
                f"Identified {svc_name} as CIDS sensor. "
                f"Mapping port {container_port}:8000"
            )
            _inject_sensor_settings(svc_data, container_port)

    return runtime_config_files


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------


def _prepare_work_dir(container_id, host_name):
    """Create and return the working directory path for a deployment."""
    host_name_safe = host_name.replace(" ", "_").lower()
    work_dir = f"/tmp/bicep_cids_{container_id}_{host_name_safe}"
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


async def _write_deployment_files(work_dir, compose_data, ruleset, runtime_config_files):
    """Write compose YAML, ruleset, and selected runtime configs to the work directory."""
    compose_file_path = os.path.join(work_dir, "docker-compose.yaml")
    with open(compose_file_path, "w") as f:
        yaml.dump(compose_data, f)

    if ruleset:
        ruleset_content = await ruleset.read_content()
        with open(os.path.join(work_dir, "rules.yaml"), "wb") as f:
            f.write(ruleset_content)

    for host_path, runtime_config in runtime_config_files.items():
        content = await runtime_config.read_content()
        with open(host_path, "wb") as f:
            if isinstance(content, str):
                f.write(content.encode("utf-8"))
            else:
                f.write(content)


# ---------------------------------------------------------------------------
# Remote host config transfer
# ---------------------------------------------------------------------------


def _get_docker_host_url(host_system):
    """Return the ``tcp://host:port`` URL for a Docker host."""
    host_ip, docker_port = host_system.get_host_and_docker_port()
    return f"tcp://{host_ip}:{docker_port}"


async def _copy_config_files_to_remote_host(docker_host_url, work_dir, runtime_config_files):
    """Copy selected runtime config files to a Docker host via a temporary alpine container."""
    host_docker = docker.DockerClient(base_url=docker_host_url)
    try:
        tmp_container = host_docker.containers.create(
            "alpine",
            "true",
            volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
        )
        try:
            # Ensure the directory exists on the host
            tmp_container.start()
            tmp_container.wait()
            tmp_container.remove()

            tmp_container = host_docker.containers.create(
                "alpine",
                ["mkdir", "-p", work_dir],
                volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
            )
            tmp_container.start()
            tmp_container.wait()

            # Build a tar archive containing all selected runtime config files
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                for host_path in runtime_config_files:
                    local_name = os.path.basename(host_path)
                    tar.add(host_path, arcname=local_name)
            tar_stream.seek(0)

            tmp_container.put_archive(work_dir, tar_stream)
            LOGGER.info(
                f"Runtime config files written to Docker host at {work_dir}"
            )
        finally:
            try:
                tmp_container.remove(force=True)
            except Exception:
                pass
    except Exception as e:
        LOGGER.error(f"Failed to write config to Docker host: {e}")
        raise
    finally:
        host_docker.close()


# ---------------------------------------------------------------------------
# Compose up & component registration
# ---------------------------------------------------------------------------


async def _run_compose_and_register(
    docker_host_url,
    work_dir,
    ids_container,
    host_system,
    services,
    db_session,
    env_vars,
):
    """Start Docker Compose services and register discovered components in the DB."""
    host_name_safe = host_system.name.replace(" ", "_").lower()
    compose_file_path = os.path.join(work_dir, "docker-compose.yaml")

    try:
        client = DockerClient(
            host=docker_host_url,
            compose_files=[compose_file_path],
            compose_project_name=f"bicep_cids_{ids_container.id}_{host_name_safe}",
        )

        LOGGER.info(
            f"Starting CIDS on {host_system.name} ({docker_host_url or 'local'})"
        )

        # Set process-level env so Compose can interpolate ${CORE_URL} etc.
        env = os.environ.copy()
        env["CORE_URL"] = get_core_url()
        if env_vars:
            env.update(env_vars)
        os.environ.update(env)

        scales = _build_scale_config(services)

        await asyncio.to_thread(
            lambda: client.compose.up(detach=True, quiet=False, scales=scales)
        )

        _register_components(client, ids_container, host_system, db_session)

    except DockerException as e:
        LOGGER.error(f"Docker Compose failed on {host_system.name}: {e}")
        try:
            with open(compose_file_path, "r") as f:
                LOGGER.debug(f"Generated compose file:\n{f.read()}")
        except Exception:
            pass
        raise Exception(f"Docker Compose failed on {host_system.name}: {e}")


def _build_scale_config(services):
    """Build a ``{service_name: count}`` dict for services that need scaling."""
    scales = {}
    for svc in services:
        count = getattr(svc, "count", 1) or 1
        if count > 1:
            scales[svc.service_name] = count
    return scales


def _register_components(client, ids_container, host_system, db_session):
    """Discover running containers and register them as IdsComponents."""
    containers = client.compose.ps()

    for c in containers:
        exposed_port = _extract_exposed_port(c)
        
        labels = getattr(c.config, "labels", None) or getattr(c, "labels", {}) or {}
        role_label = labels.get("bicep.role")

        if role_label and role_label.upper() in ["INFRA", "SENSOR", "PIPELINE"]:
            role = role_label.upper()
        else:
            role = "AGGREGATOR" if "aggregator" in c.name.lower() else "SENSOR"
        
        # If sensor, use the exposed port for the IDS instead. Important for healtchecks to work correctly!
        if role == "SENSOR":
            exposed_port = ids_container.port
        
        component = IdsComponent(
            ids_id=ids_container.id,
            name=c.name,
            role=role,
            port=exposed_port,
            host_system_id=host_system.id,
        )
        db_session.add(component)


def _extract_exposed_port(container):
    """Extract the first host-mapped port from a container's network settings."""
    ports = container.network_settings.ports
    if ports:
        for _key, bindings in ports.items():
            if bindings and len(bindings) > 0:
                return int(bindings[0]["HostPort"])
    return None
