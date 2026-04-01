from __future__ import annotations

import docker as docker_sdk
import httpx
from python_on_whales import DockerClient

from app.deployment.common import (
    DOCKER_COMPOSE_DEPLOYMENT,
    inject_config_to_url,
    inject_ruleset_to_url,
    load_configuration,
    register_deployment_plugin,
)
from app.deployment.deployment_plugins.base import DeploymentContext, DeploymentPlugin
from app.deployment.deployment_plugins.docker_compose_support import (
    ComposeAvailabilityChecker,
    ComposeDeploymentService,
    ComposeHostOperations,
    ComposeSpecManager,
)
from app.deployment.deployment_plugins.docker import (
    inject_config as inject_single_container_config,
    inject_ruleset as inject_single_container_ruleset,
    restart_docker_container,
)
from app.logger import LOGGER
from app.models.configuration import get_config_by_id
from app.models.docker_host_system import get_host_by_id
from app.models.ids_component import IdsComponent
from app.utils import get_core_url


def _build_compose_services():
    host_operations = ComposeHostOperations(
        docker_client_cls=DockerClient,
        docker_sdk_module=docker_sdk,
        ids_component_cls=IdsComponent,
        logger=LOGGER,
        get_core_url=get_core_url,
    )
    spec_manager = ComposeSpecManager(
        get_config_by_id=get_config_by_id,
        get_core_url=get_core_url,
    )
    return (
        ComposeDeploymentService(
            get_host_by_id=get_host_by_id,
            spec_manager=spec_manager,
            host_operations=host_operations,
        ),
        ComposeAvailabilityChecker(
            docker_sdk_module=docker_sdk,
            host_operations=host_operations,
            logger=LOGGER,
            http_client_cls=httpx.AsyncClient,
        ),
    )


async def start_cids_deployment(
    ids_container,
    ids_tool,
    config,
    ruleset,
    db_session,
    cids_configurations=None,
    env_vars=None,
):
    plugin = DockerComposeDeploymentPlugin()
    context = DeploymentContext(
        ids_system=ids_container,
        ids_tool=ids_tool,
        config=config,
        ruleset=ruleset,
        db_session=db_session,
        cids_configurations=list(cids_configurations or []),
        env_vars=dict(env_vars or {}),
    )
    await plugin.deploy(context)


async def deploy_docker_compose(
    ids_container,
    ids_tool,
    config,
    ruleset,
    db_session,
    cids_configurations,
    env_vars=None,
):
    deployment_service, _ = _build_compose_services()
    await deployment_service.deploy(
        ids_container=ids_container,
        config=config,
        ruleset=ruleset,
        db_session=db_session,
        cids_configurations=cids_configurations,
        env_vars=env_vars,
    )


@register_deployment_plugin
class DockerComposeDeploymentPlugin(DeploymentPlugin):
    deployment_type = DOCKER_COMPOSE_DEPLOYMENT
    startup_timeout = 120
    healthcheck_interval = 3

    async def start(self, context: DeploymentContext):
        await deploy_docker_compose(
            context.ids_system,
            context.ids_tool,
            context.config,
            context.ruleset,
            context.db_session,
            context.cids_configurations,
            env_vars=context.env_vars,
        )
        if context.db_session is not None:
            await context.db_session.refresh(
                context.ids_system,
                attribute_names=["components"],
            )

    async def inject_config(self, ids_system, configuration):
        await inject_single_container_config(ids_system, configuration)

    async def inject_ruleset(self, ids_system, ruleset):
        await inject_single_container_ruleset(ids_system, ruleset)

    async def teardown(self, ids_system, db_session):
        deployment_service, _ = _build_compose_services()
        if not getattr(ids_system, "_deployment_cleanup_done", False):
            await deployment_service.teardown(ids_system)

        for component in list(ids_system.components):
            await db_session.delete(component)

        await db_session.delete(ids_system)
        await db_session.commit()

    async def is_available(self, ids_system) -> bool:
        _, availability_checker = _build_compose_services()
        return await availability_checker.is_available(ids_system)

# TODO: update config realy necessary? --> the usecase is rather to recreate the CIDS as components ned them at start time
    async def update_config(self, ids_system, db_session, config_id: int):
        config = await load_configuration(db_session, config_id)
        if config is None:
            return

        for component in ids_system.components:
            if component.port:
                await inject_config_to_url(
                    component.get_http_url(),
                    config,
                    ids_system.id,
                    component.name,
                )
        # TODO: check if that is actually viable!
        await self._restart_components(ids_system)

    async def update_ruleset(self, ids_system, db_session, ruleset_id: int):
        ruleset = await load_configuration(db_session, ruleset_id)
        if ruleset is None:
            return

        for component in ids_system.components:
            if component.port:
                await inject_ruleset_to_url(
                    component.get_http_url(),
                    ruleset,
                )

        await self._restart_components(ids_system)

    async def _restart_components(self, ids_system):
        for component in ids_system.components:
            await restart_docker_container(component)
