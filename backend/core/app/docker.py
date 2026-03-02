import asyncio
import docker
import time
import httpx
from requests.models import Response
from app.logger import LOGGER
from app.utils import get_core_url


def get_docker_client(host_system):
    host, docker_port = host_system.get_host_and_docker_port()
    host_url = f"tcp://{host}:{docker_port}"
    try:
        client = docker.DockerClient(base_url=host_url, timeout=3)
    except Exception as e:
        LOGGER.error(e)
        raise (
            Exception(
                f"Could not create a docker client for url {host_url} \n Try to use an IP instead of hostname"
            )
        )
    return client


async def start_docker_container(
    ids_container, ids_tool, config, ruleset, db_session=None
):
    from app.cids_deployment import start_cids_deployment

    if ids_tool.deployment_type != "SINGLE_CONTAINER":
        await start_cids_deployment(
            ids_container, ids_tool, config, ruleset, db_session
        )
        return

    core_url = get_core_url()
    client = get_docker_client(ids_container.host_system)

    # ensure image is present
    # TODO 0: docker needs longer or cant take it at all when image needs to be pulled. solution ?
    # TODO: 0 activate this again for prod to ensure the image is pulled. For local tests deactivate that
    # TODO 0: more spohisticated solution maybe with env variables to be abl to pull or use image locally if needed by cgheckoing ewith the dokcer sdk if image is present
    try:
        await run_container_async(
            client=client, container=ids_container, ids_tool=ids_tool, url=core_url
        )
        await check_container_health(ids_container)
        await inject_config(ids_container, config)
        if ruleset != None:
            await inject_ruleset(ids_container, ruleset)
    finally:
        client.close()


async def run_container_async(client, ids_tool, container, url):
    image_name_and_version = f"{ids_tool.image_name}:{ids_tool.image_tag}"

    if not await image_exists(client, image_name_and_version):
        LOGGER.info(f"Image {image_name_and_version} not found, pulling...")
        await asyncio.to_thread(client.images.pull, image_name_and_version)

    docker_container = await asyncio.to_thread(
        client.containers.create,
        image=image_name_and_version,
        name=container.name,
        network_mode="host",
        environment={"PORT": container.port, "CORE_URL": url, "TZ": "UTC"},
        cap_add=["NET_ADMIN", "NET_RAW"],
    )

    await asyncio.to_thread(docker_container.start)


async def image_exists(client, image_name):
    return any(image_name in img.tags for img in client.images.list())


async def inject_config(ids_container, configuration):
    config_data = await configuration.read_content()
    files = {"file": (configuration.name, config_data, "application/octet-stream")}
    form_data = {"container_id": ids_container.id, "container_name": ids_container.name}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            ids_container.get_container_http_url() + "/configuration",
            files=files,
            data=form_data,
        )
    return response


async def inject_ruleset(ids_container, ruleset):
    ruleset_content = await ruleset.read_content()
    async with httpx.AsyncClient(timeout=10) as client:
        file = {"file": (ruleset.name, ruleset_content)}
        response = await client.post(
            ids_container.get_container_http_url() + "/ruleset", files=file
        )
    return response


async def remove_docker_container(ids_container):
    client = get_docker_client(ids_container.host_system)
    container = client.containers.get(container_id=ids_container.name)
    container.stop()
    container.remove()
    client.close()


async def check_container_health(ids_container, timeout=30):
    start_time = time.time()
    container_url = ids_container.get_container_http_url()
    url = f"{container_url}/healthcheck"
    response = Response()
    response.status_code = 500
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
        except:
            pass
        if response.status_code == 200:
            LOGGER.debug(f"Healthcheck for container {url} was sucessful")
            return True
        if time.time() - start_time > timeout:
            LOGGER.debug("Container did not become healthy in time.")
            await remove_docker_container(ids_container)
            return False
        await asyncio.sleep(2)


async def inject_config_to_url(url, configuration, system_id, component_name):
    """Inject a configuration file to a specific component URL."""
    config_data = await configuration.read_content()
    files = {"file": (configuration.name, config_data, "application/octet-stream")}
    form_data = {"container_id": system_id, "container_name": component_name}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url + "/configuration",
            files=files,
            data=form_data,
        )
    return response


async def inject_ruleset_to_url(url, ruleset):
    """Inject a ruleset file to a specific component URL."""
    ruleset_content = await ruleset.read_content()
    async with httpx.AsyncClient(timeout=10) as client:
        file = {"file": (ruleset.name, ruleset_content)}
        response = await client.post(url + "/ruleset", files=file)
    return response


async def restart_docker_container(component):
    """Restart a single Docker container (component) by name."""
    client = get_docker_client(component.host_system)
    try:
        container = client.containers.get(component.name)
        container.restart(timeout=10)
        LOGGER.info(f"Restarted component {component.name}")
    except Exception as e:
        LOGGER.error(f"Failed to restart {component.name}: {e}")
        raise
    finally:
        client.close()
