import asyncio
import os
import subprocess
from app.logger import LOGGER
from app.models.configuration import Configuration
from app.models.ids_component import IdsComponent
from app.utils import get_core_url
from app.models.docker_host_system import get_host_by_id
import docker
import yaml
from collections import defaultdict
from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException


async def start_cids_deployment(
    ids_container,
    ids_tool,
    config,
    ruleset,
    db_session,
    cids_configurations=None,
    runtime_config=None,
    env_vars=None,
):
    """
    Deploys a CIDS using Docker Compose or NixOS based on the tool's deployment type.
    """
    if ids_tool.deployment_type == "DOCKER_COMPOSE":
        await deploy_docker_compose(
            ids_container,
            ids_tool,
            config,
            ruleset,
            db_session,
            cids_configurations,
            runtime_config,
            env_vars=env_vars,
        )
    elif ids_tool.deployment_type == "NIXOS":
        await deploy_nixos(ids_container, ids_tool, config, ruleset, db_session)
    else:
        raise ValueError(f"Unsupported deployment type: {ids_tool.deployment_type}")


async def deploy_docker_compose(
    ids_container,
    ids_tool,
    config,
    ruleset,
    db_session,
    cids_configurations,
    runtime_config=None,
    env_vars=None,
):

    # Group services by host
    services_by_host = defaultdict(list)
    # Default to container's host if no specific config
    default_host_id = ids_container.host_system.id

    # Load base compose
    config_content = await config.read_content()
    compose_data = yaml.safe_load(config_content)
    LOGGER.debug(f"CIDS_CONFIG: {cids_configurations}")

    if cids_configurations:
        for svc_conf in cids_configurations:
            services_by_host[svc_conf.host_system_id].append(svc_conf)
    else:
        # Deploy everything on default host if no split config
        if "services" in compose_data:
            for svc_name in compose_data["services"]:
                services_by_host[default_host_id].append(
                    type("obj", (object,), {"service_name": svc_name, "count": 1})
                )

    # Deploy for each host
    for host_id, services in services_by_host.items():
        host_system = await get_host_by_id(db_session, host_id)

        # Filter Compose Data
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

        if not host_compose_data["services"]:
            continue

        # Prepare working directory
        host_name_safe = host_system.name.replace(" ", "_").lower()
        work_dir = f"/tmp/bicep_cids_{ids_container.id}_{host_name_safe}"
        os.makedirs(work_dir, exist_ok=True)

        # Inject config mount and sensor port mappings
        needs_config_on_host = False
        services_needing_config = []
        for svc_name, svc_data in host_compose_data["services"].items():
            labels = svc_data.get("labels", {})
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

            if mount_path:
                needs_config_on_host = True
                services_needing_config.append((svc_name, svc_data, mount_path))

                # Add volume mount using absolute host path
                volume_entry = f"{work_dir}/bicep_config:{mount_path}"
                if "volumes" not in svc_data:
                    svc_data["volumes"] = []
                # Remove any existing mount to the same container path
                svc_data["volumes"] = [
                    v
                    for v in svc_data["volumes"]
                    if not (isinstance(v, str) and v.endswith(f":{mount_path}"))
                ]
                svc_data["volumes"].append(volume_entry)
                LOGGER.info(f"Will mount config into {svc_name} at {mount_path}")
                
            if is_sensor:
                LOGGER.info(f"Identified {svc_name} as CIDS sensor. Mapping port {ids_container.port}:8000")
                if "ports" not in svc_data:
                    svc_data["ports"] = []
                
                # Check if 8000 is already mapped, if not add mapping
                has_port_mapping = any(
                    str(p).endswith(":8000") or str(p) == "8000" 
                    for p in svc_data["ports"]
                )
                if not has_port_mapping:
                    svc_data["ports"].append(f"{ids_container.port}:8000")

        # Write partial docker-compose.yaml
        compose_file_path = os.path.join(work_dir, "docker-compose.yaml")
        with open(compose_file_path, "w") as f:
            yaml.dump(host_compose_data, f)

        # Write Ruleset if available
        if ruleset:
            ruleset_content = await ruleset.read_content()
            ruleset_path = os.path.join(work_dir, "rules.yaml")
            with open(ruleset_path, "wb") as f:
                f.write(ruleset_content)

        # Write Runtime Config if available
        if runtime_config:
            content = await runtime_config.read_content()
            filename = os.path.basename(runtime_config.file_path)
            config_path = os.path.join(work_dir, filename)
            with open(config_path, "wb") as f:
                if isinstance(content, str):
                    f.write(content.encode("utf-8"))
                else:
                    f.write(content)

        # Determine Docker Host Connection
        host_ip, docker_port = host_system.get_host_and_docker_port()
        docker_host_url = f"tcp://{host_ip}:{docker_port}"

        # Write runtime config file to Docker HOST filesystem via temporary container
        if needs_config_on_host and runtime_config:
            import io
            import tarfile

            runtime_content = await runtime_config.read_content()
            if isinstance(runtime_content, str):
                runtime_content = runtime_content.encode("utf-8")

            host_docker = docker.DockerClient(base_url=docker_host_url)
            try:
                # Create a stopped container with /tmp bind-mounted from the host
                tmp_container = host_docker.containers.create(
                    "alpine",
                    "true",
                    volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
                )
                try:
                    # Ensure the directory exists on the host
                    tmp_container.start()
                    tmp_container.wait()
                    # Recreate with mkdir
                    tmp_container.remove()
                    tmp_container = host_docker.containers.create(
                        "alpine",
                        ["mkdir", "-p", work_dir],
                        volumes={"/tmp": {"bind": "/tmp", "mode": "rw"}},
                    )
                    tmp_container.start()
                    tmp_container.wait()

                    # Build a tar archive containing the config file
                    tar_stream = io.BytesIO()
                    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                        file_info = tarfile.TarInfo(name="bicep_config")
                        file_info.size = len(runtime_content)
                        tar.addfile(file_info, io.BytesIO(runtime_content))
                    tar_stream.seek(0)

                    # Copy the tar into the container at the work_dir path
                    tmp_container.put_archive(work_dir, tar_stream)
                    LOGGER.info(
                        f"Config file written to Docker host at {work_dir}/bicep_config"
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

        try:
            client = DockerClient(
                host=docker_host_url,
                compose_files=[compose_file_path],
                compose_project_name=f"bicep_cids_{ids_container.id}_{host_name_safe}",
            )

            LOGGER.info(
                f"Starting CIDS on {host_system.name} ({docker_host_url or 'local'})"
            )

            # Env variables
            env = os.environ.copy()
            env["CORE_URL"] = get_core_url()
            # Merge user-provided environment variables
            if env_vars:
                env.update(env_vars)
            os.environ.update(env)

            # Build scale configuration from service counts
            scales = {}
            for svc in services:
                count = getattr(svc, "count", 1) or 1
                if count > 1:
                    scales[svc.service_name] = count

            # Up
            # python-on-whales up runs synchronously (or blocking), but we are in async function.
            # Ideally we run this in executor to avoid blocking event loop.
            def run_compose_up():
                client.compose.up(detach=True, quiet=False, scales=scales)

            await asyncio.to_thread(run_compose_up)

            # Verify and Register Components
            # python-on-whales 'ps' returns list of Container objects (python-on-whales objects)
            containers = client.compose.ps()

            for c in containers:
                # c is a python_on_whales.components.container.cli_wrapper.Container
                role = "SENSOR"
                if "aggregator" in c.name.lower():
                    role = "AGGREGATOR"

                exposed_port = None
                # Network settings extraction
                # c.network_settings.ports is a dict
                ports = c.network_settings.ports
                if ports:
                    for k, v in ports.items():
                        if v and len(v) > 0:
                            # v is list of dicts, e.g. [{'HostIp': '0.0.0.0', 'HostPort': '32768'}]
                            exposed_port = int(v[0]["HostPort"])
                            break

                component = IdsComponent(
                    container_id=ids_container.id,
                    name=c.name,
                    role=role,
                    port=exposed_port,
                    host_system_id=host_system.id,
                )
                db_session.add(component)

        except DockerException as e:
            LOGGER.error(f"Docker Compose failed on {host_system.name}: {e}")
            # Log the generated compose file for debugging
            try:
                with open(compose_file_path, "r") as f:
                    LOGGER.debug(f"Generated compose file:\n{f.read()}")
            except Exception:
                pass
            raise Exception(f"Docker Compose failed on {host_system.name}: {e}")

    await db_session.commit()


async def deploy_nixos(ids_container, ids_tool, config, ruleset, db_session):
    # Placeholder for NixOS logic
    LOGGER.warning("NixOS deployment not fully implemented yet.")
    pass
