from __future__ import annotations

import logging
from types import SimpleNamespace

import docker as docker_sdk
import httpx
from python_on_whales import DockerClient
from app.deployment.common import (
    DOCKER_COMPOSE_DEPLOYMENT,
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
)
from app.models.configuration import get_config_by_id
from app.models.docker_host_system import get_host_by_id
from app.models.ids_component import IdsComponent
from app.models.ids_system import mark_container_as_deleted
from app.utils import get_core_url

logger = logging.getLogger('bicep.docker_compose')


def _build_compose_services():
    host_operations = ComposeHostOperations(
        docker_client_cls=DockerClient,
        docker_sdk_module=docker_sdk,
        ids_component_cls=IdsComponent,
        logger=logger,
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
            logger=logger,
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
        # When restarting/updating, we need to clear old components first to avoid duplicates
        # unless teardown was already called and handled it.
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

    async def teardown(self, ids_system, db_session, delete_system=True):
        deployment_service, _ = _build_compose_services()
        if not getattr(ids_system, "_deployment_cleanup_done", False):
            await deployment_service.teardown(ids_system)

        for component in list(ids_system.components):
            await db_session.delete(component)

        if delete_system:
            await mark_container_as_deleted(db_session, ids_system)

        await db_session.commit()

    async def is_available(self, ids_system) -> bool:
        _, availability_checker = _build_compose_services()
        return await availability_checker.is_available(ids_system)

    def _capture_service_deployment_state(self, ids_system):
        snapshots = {}
        for component in ids_system.components:
            service_name = component.service_name
            host_system_id = component.host_system_id or ids_system.host_system_id
            if service_name is None or host_system_id is None:
                continue

            snapshots[(host_system_id, service_name)] = SimpleNamespace(
                service_name=service_name,
                count=component.count or 1,
                runtime_configuration_id=component.runtime_configuration_id,
                host_system_id=host_system_id,
            )

        return list(snapshots.values())

    async def update_config(self, ids_system, db_session, config_id: int):
        logger.info(f"Re-deploying CIDS {ids_system.name} to apply changes.")

        # Persist the per-service deployment state before teardown removes the
        # component rows that tell us where each compose service belongs.
        cids_configurations = self._capture_service_deployment_state(ids_system)
        await self.teardown(ids_system, db_session, delete_system=False)

        await db_session.refresh(ids_system, attribute_names=["host_system"])

        config = await load_configuration(db_session, ids_system.configuration_id)
        ruleset = None
        if ids_system.ruleset_id:
            ruleset = await load_configuration(db_session, ids_system.ruleset_id)

        context = DeploymentContext(
            ids_system=ids_system,
            ids_tool=ids_system.ids_tool,
            config=config,
            ruleset=ruleset,
            db_session=db_session,
            cids_configurations=cids_configurations,
        )
        await self.start(context)

    async def update_components(self, ids_system, db_session, components: list):
        changed_service_keys = {
            (component.host_system_id, component.service_name)
            for component in components
            if getattr(component, "service_name", None)
        }
        if not changed_service_keys:
            return

        deployment_service, _ = _build_compose_services()
        config = await load_configuration(db_session, ids_system.configuration_id)
        if config is None:
            return

        ruleset = None
        if ids_system.ruleset_id:
            ruleset = await load_configuration(db_session, ids_system.ruleset_id)

        await deployment_service.redeploy_services(
            ids_container=ids_system,
            config=config,
            ruleset=ruleset,
            db_session=db_session,
            cids_configurations=self._capture_service_deployment_state(ids_system),
            changed_service_keys=changed_service_keys,
        )

    async def update_ruleset(self, ids_system, db_session, ruleset_id: int):
        logger.info(f"Re-deploying CIDS {ids_system.name} to apply ruleset update.")
        # Identical strategy to update_config for CIDS
        await self.update_config(ids_system, db_session, ids_system.configuration_id)
