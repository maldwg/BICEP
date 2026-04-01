from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deployment.deployment_plugins.base import DeploymentContext, DeploymentPlugin
from app.logger import LOGGER
from app.models.configuration import Configuration
from app.models.ids_tool import get_ids_by_id

SINGLE_CONTAINER_DEPLOYMENT = "SINGLE_CONTAINER"
DOCKER_COMPOSE_DEPLOYMENT = "DOCKER_COMPOSE"


_DEPLOYMENT_PLUGINS: dict[str, type[DeploymentPlugin]] = {}


def normalize_deployment_type(deployment_type: Any) -> str:
    if not isinstance(deployment_type, str):
        return SINGLE_CONTAINER_DEPLOYMENT

    normalized = deployment_type.strip().upper()
    if not normalized:
        return SINGLE_CONTAINER_DEPLOYMENT
    return normalized


def register_deployment_plugin(plugin_cls: type[DeploymentPlugin]):
    _DEPLOYMENT_PLUGINS[normalize_deployment_type(plugin_cls.deployment_type)] = (
        plugin_cls
    )
    return plugin_cls


_plugins_loaded = False

def _ensure_builtin_plugins_loaded():
    global _plugins_loaded
    if not _plugins_loaded:
        import app.deployment.deployment_plugins.docker
        import app.deployment.deployment_plugins.docker_compose
        _plugins_loaded = True

def get_deployment_plugin(deployment_type: Any) -> DeploymentPlugin:
    _ensure_builtin_plugins_loaded()
    normalized = normalize_deployment_type(deployment_type)
    plugin_cls = _DEPLOYMENT_PLUGINS.get(normalized)
    if plugin_cls is None:
        raise ValueError(f"Unsupported deployment type: {deployment_type}")
    return plugin_cls()


async def load_configuration(db_session: AsyncSession, configuration_id: int):
    stmt = select(Configuration).where(Configuration.id == configuration_id)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def wait_for_condition(check, timeout: float, interval: float) -> bool:
    start_time = time.monotonic()
    while True:
        if await check():
            return True
        if time.monotonic() - start_time > timeout:
            return False
        await asyncio.sleep(interval)


async def inject_config_to_url(url, configuration, system_id, component_name):
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
    ruleset_content = await ruleset.read_content()
    async with httpx.AsyncClient(timeout=10) as client:
        files = {"file": (ruleset.name, ruleset_content)}
        response = await client.post(url + "/ruleset", files=files)
    return response


async def resolve_ids_tool(ids_system, db_session: AsyncSession | None = None, ids_tool=None):
    if ids_tool is not None:
        return ids_tool

    cached_tool = ids_system.__dict__.get("ids_tool")
    if cached_tool is not None:
        return cached_tool

    if db_session is None:
        raise ValueError(
            f"Cannot resolve deployment plugin for IDS {ids_system.id} without a database session."
        )

    resolved_tool = await get_ids_by_id(db_session, ids_system.ids_tool_id)
    if resolved_tool is None:
        raise ValueError(f"IDS tool {ids_system.ids_tool_id} was not found.")
    return resolved_tool


async def get_plugin_for_system(
    ids_system, db_session: AsyncSession | None = None, ids_tool=None
) -> DeploymentPlugin:
    resolved_tool = await resolve_ids_tool(
        ids_system, db_session=db_session, ids_tool=ids_tool
    )
    return get_deployment_plugin(getattr(resolved_tool, "deployment_type", None))


async def deploy_ids(
    ids_system,
    ids_tool,
    config,
    ruleset,
    db_session: AsyncSession | None = None,
    runtime_configuration=None,
    cids_configurations=None,
    env_vars=None,
):
    context = DeploymentContext(
        ids_system=ids_system,
        ids_tool=ids_tool,
        config=config,
        ruleset=ruleset,
        db_session=db_session,
        runtime_configuration=runtime_configuration,
        cids_configurations=list(cids_configurations or []),
        env_vars=dict(env_vars or {}),
    )
    plugin = get_deployment_plugin(getattr(ids_tool, "deployment_type", None))
    await plugin.deploy(context)


async def teardown_ids(ids_system, db_session: AsyncSession):
    plugin = await get_plugin_for_system(ids_system, db_session=db_session)
    await plugin.teardown(ids_system, db_session)


async def update_ids_config(ids_system, db_session: AsyncSession, config_id: int):
    plugin = await get_plugin_for_system(ids_system, db_session=db_session)
    await plugin.update_config(ids_system, db_session, config_id)


async def update_ids_ruleset(ids_system, db_session: AsyncSession, ruleset_id: int):
    plugin = await get_plugin_for_system(ids_system, db_session=db_session)
    await plugin.update_ruleset(ids_system, db_session, ruleset_id)


async def is_ids_available(ids_system, db_session: AsyncSession | None = None) -> bool:
    try:
        plugin = await get_plugin_for_system(ids_system, db_session=db_session)
    except ValueError as exc:
        LOGGER.error(exc)
        return False
    return await plugin.is_available(ids_system)
