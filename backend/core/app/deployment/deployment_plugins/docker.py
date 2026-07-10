from __future__ import annotations

import asyncio
import logging
import os
import time

import docker as docker_sdk
import httpx
from docker import DockerClient
from docker.errors import ImageNotFound, APIError, NotFound
from docker.models.containers import Container
from requests.models import Response

from app.deployment.common import (
    SINGLE_CONTAINER_DEPLOYMENT,
    inject_config_to_url,
    inject_ruleset_to_url,
    register_deployment_plugin,
)
from app.deployment.deployment_plugins.base import DeploymentContext, DeploymentPlugin
from app.models.ids_system import mark_container_as_deleted
from app.utils import get_core_url

logger = logging.getLogger('bicep.deployment_plugin.single_container')

DOCKER_DEPLOYMENT_CLIENT_TIMEOUT = int(
    os.getenv("DOCKER_DEPLOYMENT_CLIENT_TIMEOUT_SECONDS", "600")
)
DOCKER_CONTROL_CLIENT_TIMEOUT = int(
    os.getenv("DOCKER_CONTROL_CLIENT_TIMEOUT_SECONDS", "10")
)


def _split_image_reference(image_reference: str) -> tuple[str, str | None]:
    if "@" in image_reference:
        return image_reference, None

    last_slash = image_reference.rfind("/")
    last_colon = image_reference.rfind(":")
    if last_colon > last_slash:
        return image_reference[:last_colon], image_reference[last_colon + 1:]

    return image_reference, None


def get_docker_client(host_system, timeout: int | None = None):
    if host_system.is_core_host():
        socket_path = os.getenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock")
        if os.path.exists(socket_path):
            host_url = f"unix://{socket_path}"
        else:
            logger.warning(
                "Unix socket %s not found, falling back to TCP for core host", socket_path
            )
            host, docker_port = host_system.get_host_and_docker_port()
            host_url = f"tcp://{host}:{docker_port}"
    else:
        host, docker_port = host_system.get_host_and_docker_port()
        host_url = f"tcp://{host}:{docker_port}"
    try:
        client = docker_sdk.DockerClient(
            base_url=host_url,
            timeout=timeout or DOCKER_DEPLOYMENT_CLIENT_TIMEOUT,
        )
    except Exception as exc:
        logger.error(exc)
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


def image_exists_blocking(client, image_name):
    try:
        client.images.get(image_name)
        return True
    except ImageNotFound:
        return False
    except Exception:
        return any(image_name in image.tags for image in client.images.list())


def pull_image_blocking(client, image_name):
    logger.info("Pulling Image: image_name=%s", image_name)
    repository, tag = _split_image_reference(image_name)
    if tag is None:
        return client.images.pull(repository)
    return client.images.pull(repository=repository, tag=tag)


def ensure_image_present_blocking(client, image_name):
    try:
        pull_image_blocking(client, image_name)
    except Exception as exc:
        if image_exists_blocking(client, image_name):
            logger.warning(
                "Image pull failed for %s, using existing local image instead: %s",
                image_name,
                exc,
            )
            return
        raise Exception(f"Could not pull required image {image_name}: {exc}") from exc


async def ensure_image_present(client, image_name):
    await asyncio.to_thread(ensure_image_present_blocking, client, image_name)


async def run_container_async(client, ids_tool, container, url):
    image_name_and_version = f"{ids_tool.image_name}:{ids_tool.image_tag}"

    await ensure_image_present(client, image_name_and_version)

    try:
        logger.info("Creating docker container: name=%s image=%s", container.name, image_name_and_version)
        docker_container: Container = await asyncio.to_thread(
            client.containers.create,
            image=image_name_and_version,
            name=container.name,
            network_mode="host",
            environment={"PORT": container.port, "CORE_URL": url, "TZ": "UTC"},
            cap_add=["NET_ADMIN", "NET_RAW"],
        )
        logger.info("Docker container created successfully: name=%s", container.name)
    except (ImageNotFound , APIError) as exc:
        logger.error("Error during container creation: name=%s error=%s", container.name, exc)
        raise

    try:
        await asyncio.to_thread(docker_container.start)
        logger.info("Docker container started successfully: name=%s", container.name)
    except APIError as exc:
        logger.error("Error during container startup: name=%s error=%s", container.name, exc)
        raise


async def image_exists(client, image_name):
    return await asyncio.to_thread(image_exists_blocking, client, image_name)


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
    client: DockerClient = get_docker_client(
        ids_container.host_system,
        timeout=DOCKER_CONTROL_CLIENT_TIMEOUT,
    )
    try:
        container = client.containers.get(container_id=ids_container.name)
    except (NotFound , APIError) as exc:
        logger.error("Error during stopping container: name=%s error=%s", ids_container.name, exc)
        return

    try:
        container.stop()
    except APIError as exc:
        logger.error("Error during stopping container: name=%s error=%s", container.name, exc)
        raise

    try:
        container.remove()
    except APIError as exc:
        logger.error("Error during removing container: name=%s error=%s", container.name, exc)
        raise


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
    client = get_docker_client(
        component.host_system,
        timeout=DOCKER_CONTROL_CLIENT_TIMEOUT,
    )
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
        if healthy:
            logger.info(
                "IDS became healthy: ids_system=%s",
                context.ids_system.name
            )
        else:
            raise Exception(
                f"IDS {context.ids_system.id} did not become healthy in time."
            )

    async def inject_config(self, ids_system, configuration):
        await inject_config(ids_system, configuration)

    async def inject_ruleset(self, ids_system, ruleset):
        await inject_ruleset(ids_system, ruleset)

    async def teardown(self, ids_system, db_session):
        await remove_docker_container(ids_system)
        await mark_container_as_deleted(db_session, ids_system)
        await db_session.commit()

    async def is_available(self, ids_system) -> bool:
        return await check_container_health(ids_system)
