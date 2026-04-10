from __future__ import annotations
import asyncio
import time
import docker as docker_sdk
import httpx
from requests.models import Response
from app.deployment.common import (
    SINGLE_CONTAINER_DEPLOYMENT,
    inject_config_to_url,
    inject_ruleset_to_url,
    register_deployment_plugin,
)
from app.deployment.deployment_plugins.base import DeploymentContext, DeploymentPlugin
from app.logger import LOGGER
from app.models.ids_system import mark_container_as_deleted
from app.utils import get_core_url


def get_docker_client(host_system):
    host, docker_port = host_system.get_host_and_docker_port()
    host_url = f"tcp://{host}:{docker_port}"
    try:
        client = docker_sdk.DockerClient(base_url=host_url, timeout=3)
    except Exception as exc:
        LOGGER.error(exc)
        raise Exception(
            f"Could not create a docker client for url {host_url} \n"
            "Try to use an IP instead of hostname"
        )
    return client


async def start_docker_container(
    ids_container, ids_tool, config, ruleset, db_session=None
):
    plugin = SingleContainerDeploymentPlugin()
    context = DeploymentContext(
        ids_system=ids_container,
        ids_tool=ids_tool,
        config=config,
        ruleset=ruleset,
        db_session=db_session,
    )
    await plugin.deploy(context)


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
    return any(image_name in image.tags for image in client.images.list())




async def inject_config(ids_container, configuration):
    """
    Injects the given configuration into the IDS container by sending it to the appropriate endpoint.
    Necessary to be a standalone function to be used in both the plugin and the generic start function.
    """
    return await inject_config_to_url(
        ids_container.get_container_http_url(),
        configuration,
        ids_container.id,
        ids_container.name,
    )


async def inject_ruleset(ids_container, ruleset):
    """
    Injects the given ruleset into the IDS container by sending it to the appropriate endpoint.
    Necessary to be a standalone function to be used in both the plugin and the generic start function.
    """
    return await inject_ruleset_to_url(
        ids_container.get_container_http_url(),
        ruleset,
    )


async def remove_docker_container(ids_container):
    client = get_docker_client(ids_container.host_system)
    try:
        container = client.containers.get(container_id=ids_container.name)
        container.stop()
        container.remove()
    finally:
        client.close()


async def check_container_health(ids_container, timeout=90, cleanup_on_failure=True):
    start_time = time.time()
    container_url = ids_container.get_container_http_url()
    url = f"{container_url}/healthcheck"
    response = Response()
    response.status_code = 500

    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
        except Exception:
            pass

        if response.status_code == 200:
            return True

        if time.time() - start_time > timeout:
            if cleanup_on_failure:
                await remove_docker_container(ids_container)
            return False

        await asyncio.sleep(2)


async def restart_docker_container(component):
    client = get_docker_client(component.host_system)
    try:
        container = client.containers.get(component.name)
        container.restart(timeout=10)
    finally:
        client.close()


@register_deployment_plugin
class SingleContainerDeploymentPlugin(DeploymentPlugin):
    deployment_type = SINGLE_CONTAINER_DEPLOYMENT

    async def start(self, context: DeploymentContext):
        client = get_docker_client(context.ids_system.host_system)
        try:
            await run_container_async(
                client=client,
                container=context.ids_system,
                ids_tool=context.ids_tool,
                url=get_core_url(),
            )
        finally:
            client.close()

    async def wait_until_healthy(self, context: DeploymentContext):
        healthy = await check_container_health(
            context.ids_system,
            timeout=self.startup_timeout,
        )
        if not healthy:
            raise Exception(
                f"IDS {context.ids_system.id} did not become healthy in time."
            )

    async def inject_config(self, ids_system, configuration):
        await inject_config(ids_system, configuration)

    async def inject_ruleset(self, ids_system, ruleset):
        await inject_ruleset(ids_system, ruleset)

    async def teardown(self, ids_system, db_session):
        try:
            await remove_docker_container(ids_system)
        except Exception as exc:
            LOGGER.error(f"Teardown error: {exc}")
        await mark_container_as_deleted(db_session, ids_system)
        await db_session.commit()

    async def is_available(self, ids_system) -> bool:
        return await check_container_health(ids_system)
