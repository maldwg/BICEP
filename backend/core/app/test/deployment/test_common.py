import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.deployment import common
from app.deployment.deployment_plugins.base import DeploymentPlugin


class DummyPlugin(DeploymentPlugin):
    deployment_type = " custom "

    async def start(self, context):
        return None

    async def inject_config(self, ids_system, configuration):
        return None

    async def inject_ruleset(self, ids_system, ruleset):
        return None

    async def teardown(self, ids_system, db_session):
        return None

    async def is_available(self, ids_system) -> bool:
        return True


def test_normalize_deployment_type_defaults_to_single_container():
    assert common.normalize_deployment_type(None) == common.SINGLE_CONTAINER_DEPLOYMENT
    assert common.normalize_deployment_type("") == common.SINGLE_CONTAINER_DEPLOYMENT
    assert (
        common.normalize_deployment_type(" docker_compose ")
        == common.DOCKER_COMPOSE_DEPLOYMENT
    )


def test_register_and_get_deployment_plugin():
    previous_registry = dict(common._DEPLOYMENT_PLUGINS)
    common._DEPLOYMENT_PLUGINS.clear()
    try:
        common.register_deployment_plugin(DummyPlugin)
        plugin = common.get_deployment_plugin("custom")
        assert isinstance(plugin, DummyPlugin)
    finally:
        common._DEPLOYMENT_PLUGINS.clear()
        common._DEPLOYMENT_PLUGINS.update(previous_registry)


@pytest.mark.asyncio
async def test_wait_for_condition_times_out():
    checks = 0

    async def check():
        nonlocal checks
        checks += 1
        return False

    with patch(
        "app.deployment.common.time.monotonic",
        side_effect=[0.0, 0.0, 0.2],
    ):
        with patch(
            "app.deployment.common.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await common.wait_for_condition(check, timeout=0.1, interval=0.01)

    assert result is False
    assert checks == 2
    mock_sleep.assert_awaited_once_with(0.01)


@pytest.mark.asyncio
async def test_resolve_ids_tool_prefers_explicit_and_cached_values():
    ids_system = MagicMock()
    explicit_tool = MagicMock()
    cached_tool = MagicMock()

    assert (
        await common.resolve_ids_tool(ids_system, ids_tool=explicit_tool)
        is explicit_tool
    )

    ids_system.__dict__["ids_tool"] = cached_tool
    assert await common.resolve_ids_tool(ids_system) is cached_tool


@pytest.mark.asyncio
async def test_resolve_ids_tool_errors_when_lookup_is_impossible():
    ids_system = MagicMock()
    ids_system.id = 12
    ids_system.ids_tool_id = 99

    with pytest.raises(ValueError, match="without a database session"):
        await common.resolve_ids_tool(ids_system)

    with patch(
        "app.deployment.common.get_ids_by_id",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(ValueError, match="IDS tool 99 was not found"):
            await common.resolve_ids_tool(ids_system, db_session=AsyncMock())


@pytest.mark.asyncio
async def test_deploy_and_update_helpers_delegate_to_plugin():
    plugin = MagicMock()
    plugin.deploy = AsyncMock()
    plugin.teardown = AsyncMock()
    plugin.update_config = AsyncMock()
    plugin.update_ruleset = AsyncMock()
    plugin.is_available = AsyncMock(return_value=True)

    ids_system = MagicMock()
    ids_tool = MagicMock()
    ids_tool.deployment_type = "custom"
    db_session = AsyncMock()

    with patch(
        "app.deployment.common.get_deployment_plugin",
        return_value=plugin,
    ):
        await common.deploy_ids(
            ids_system,
            ids_tool,
            config="cfg",
            ruleset="rules",
            db_session=db_session,
            cids_configurations=[1],
            env_vars={"A": "B"},
        )

    context = plugin.deploy.await_args.args[0]
    assert context.ids_system is ids_system
    assert context.ids_tool is ids_tool
    assert context.cids_configurations == [1]
    assert context.env_vars == {"A": "B"}

    with patch(
        "app.deployment.common.get_plugin_for_system",
        AsyncMock(return_value=plugin),
    ):
        await common.teardown_ids(ids_system, db_session)
        await common.update_ids_config(ids_system, db_session, 5)
        await common.update_ids_ruleset(ids_system, db_session, 6)
        assert await common.is_ids_available(ids_system, db_session) is True

    plugin.teardown.assert_awaited_once_with(ids_system, db_session)
    plugin.update_config.assert_awaited_once_with(ids_system, db_session, 5)
    plugin.update_ruleset.assert_awaited_once_with(ids_system, db_session, 6)
    plugin.is_available.assert_awaited_once_with(ids_system)


@pytest.mark.asyncio
async def test_is_ids_available_returns_false_when_plugin_lookup_fails():
    ids_system = MagicMock()

    with patch(
        "app.deployment.common.get_plugin_for_system",
        AsyncMock(side_effect=ValueError("broken")),
    ):
        with patch("app.deployment.common.LOGGER.error") as mock_log_error:
            result = await common.is_ids_available(ids_system)

    assert result is False
    mock_log_error.assert_called_once()
