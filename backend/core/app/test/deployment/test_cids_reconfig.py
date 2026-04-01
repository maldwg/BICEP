import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.ids_system import CidsSystem
from app.models.ids_component import IdsComponent
from app.models.docker_host_system import DockerHostSystem
from app.models.ids_tool import IdsTool
from app.utils import STATUS


@pytest.fixture
def mock_host_system():
    return DockerHostSystem(
        id=1,
        name="TestHost",
        host="192.168.1.100",
        docker_port=2375,
    )


@pytest.fixture
def mock_components(mock_host_system):
    sensor = IdsComponent(
        id=1,
        name="bicep_cids_1_sensor",
        role="SENSOR",
        port=8081,
        host_system=mock_host_system,
    )

    aggregator = IdsComponent(
        id=2,
        name="bicep_cids_1_aggregator",
        role="AGGREGATOR",
        port=8082,
        host_system=mock_host_system,
    )

    return [sensor, aggregator]


@pytest.fixture
def mock_component_no_port(mock_host_system):
    """A component without an exposed port (e.g. internal-only service)."""
    return IdsComponent(
        id=3,
        name="bicep_cids_1_internal",
        role="INTERNAL",
        port=None,
        host_system=mock_host_system,
    )


@pytest.fixture
def cids_system(mock_host_system, mock_components):
    ids_tool = IdsTool(
        id=1,
        name="Test CIDS Tool",
        ids_type="CIDS",
        analysis_method="NETWORK",
        requires_ruleset=True,
        image_name="test/image",
        image_tag="latest",
        deployment_type="DOCKER_COMPOSE",
    )
    return CidsSystem(
        id=1,
        name="Test CIDS",
        port=8080,
        status=STATUS.IDLE.value,
        ids_tool_id=ids_tool.id,
        ids_tool=ids_tool,
        host_system=mock_host_system,
        components=mock_components,
    )


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.id = 10
    config.name = "snort.conf"
    config.read_content = AsyncMock(return_value=b"config content")
    return config


@pytest.fixture
def mock_ruleset():
    ruleset = MagicMock()
    ruleset.id = 20
    ruleset.name = "local.rules"
    ruleset.read_content = AsyncMock(return_value=b"rule content")
    return ruleset


# ==================== update_config tests ====================


@pytest.mark.asyncio
@patch(
    "app.deployment.deployment_plugins.docker_compose.load_configuration",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.inject_config_to_url",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.restart_docker_container",
    new_callable=AsyncMock,
)
async def test_cids_update_config_propagates_to_all_components(
    mock_restart, mock_inject, mock_load_configuration, cids_system, mock_config
):
    """update_config should inject config to every component with a port and then restart all."""
    db = AsyncMock()
    mock_load_configuration.return_value = mock_config

    await cids_system.update_config(db, config_id=10)

    # Should inject config to both sensor and aggregator
    assert mock_inject.call_count == 2
    mock_inject.assert_any_call(
        "http://192.168.1.100:8081", mock_config, 1, "bicep_cids_1_sensor"
    )
    mock_inject.assert_any_call(
        "http://192.168.1.100:8082", mock_config, 1, "bicep_cids_1_aggregator"
    )

    # Should restart both components
    assert mock_restart.call_count == 2


@pytest.mark.asyncio
@patch(
    "app.deployment.deployment_plugins.docker_compose.load_configuration",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.inject_config_to_url",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.restart_docker_container",
    new_callable=AsyncMock,
)
async def test_cids_update_config_skips_components_without_port(
    mock_restart,
    mock_inject,
    mock_load_configuration,
    cids_system,
    mock_config,
    mock_component_no_port,
):
    """Components without a port should not receive config injection."""
    cids_system.components.append(mock_component_no_port)

    db = AsyncMock()
    mock_load_configuration.return_value = mock_config

    await cids_system.update_config(db, config_id=10)

    # Only 2 components have ports (sensor + aggregator), not the internal one
    assert mock_inject.call_count == 2
    # But all 3 components get restarted
    assert mock_restart.call_count == 3


@pytest.mark.asyncio
@patch(
    "app.deployment.deployment_plugins.docker_compose.load_configuration",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.inject_config_to_url",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.restart_docker_container",
    new_callable=AsyncMock,
)
async def test_cids_update_config_no_op_for_missing_config(
    mock_restart, mock_inject, mock_load_configuration, cids_system
):
    """If the config ID doesn't exist, nothing should happen."""
    db = AsyncMock()
    mock_load_configuration.return_value = None

    await cids_system.update_config(db, config_id=999)

    mock_inject.assert_not_called()
    mock_restart.assert_not_called()


# ==================== update_ruleset tests ====================


@pytest.mark.asyncio
@patch(
    "app.deployment.deployment_plugins.docker_compose.load_configuration",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.inject_ruleset_to_url",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.restart_docker_container",
    new_callable=AsyncMock,
)
async def test_cids_update_ruleset_propagates_to_all_components(
    mock_restart, mock_inject_ruleset, mock_load_configuration, cids_system, mock_ruleset
):
    """update_ruleset should inject ruleset to every component with a port and restart all."""
    db = AsyncMock()
    mock_load_configuration.return_value = mock_ruleset

    await cids_system.update_ruleset(db, ruleset_id=20)

    assert mock_inject_ruleset.call_count == 2
    mock_inject_ruleset.assert_any_call("http://192.168.1.100:8081", mock_ruleset)
    mock_inject_ruleset.assert_any_call("http://192.168.1.100:8082", mock_ruleset)

    assert mock_restart.call_count == 2


@pytest.mark.asyncio
@patch(
    "app.deployment.deployment_plugins.docker_compose.load_configuration",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.inject_ruleset_to_url",
    new_callable=AsyncMock,
)
@patch(
    "app.deployment.deployment_plugins.docker_compose.restart_docker_container",
    new_callable=AsyncMock,
)
async def test_cids_update_ruleset_no_op_for_missing_ruleset(
    mock_restart, mock_inject_ruleset, mock_load_configuration, cids_system
):
    """If the ruleset ID doesn't exist, nothing should happen."""
    db = AsyncMock()
    mock_load_configuration.return_value = None

    await cids_system.update_ruleset(db, ruleset_id=999)

    mock_inject_ruleset.assert_not_called()
    mock_restart.assert_not_called()


# ==================== restart_docker_container tests ====================


@pytest.mark.asyncio
@patch("app.deployment.deployment_plugins.docker.get_docker_client")
async def test_restart_docker_container_calls_docker_api(
    mock_get_client, mock_components
):
    from app.deployment.deployment_plugins.docker import restart_docker_container

    mock_docker_client = MagicMock()
    mock_container = MagicMock()
    mock_docker_client.containers.get.return_value = mock_container
    mock_get_client.return_value = mock_docker_client

    component = mock_components[0]
    await restart_docker_container(component)

    mock_get_client.assert_called_once_with(component.host_system)
    mock_docker_client.containers.get.assert_called_once_with(component.name)
    mock_container.restart.assert_called_once_with(timeout=10)
    mock_docker_client.close.assert_called_once()


# ==================== IdsComponent.get_http_url tests ====================


def test_ids_component_get_http_url_remote_host():
    """Component on a remote host should use that host's address."""
    host = DockerHostSystem(id=1, name="RemoteHost", host="10.0.0.5", docker_port=2375)
    component = IdsComponent(
        id=1, name="sensor", role="SENSOR", port=8081, host_system=host
    )
    assert component.get_http_url() == "http://10.0.0.5:8081"


@patch("app.utils.get_core_host_ip", return_value="172.17.0.1")
def test_ids_component_get_http_url_localhost(mock_core_ip):
    """Component on localhost should resolve to the core host IP."""
    host = DockerHostSystem(id=1, name="localhost", host="localhost", docker_port=2375)
    component = IdsComponent(
        id=1, name="sensor", role="SENSOR", port=8081, host_system=host
    )
    assert component.get_http_url() == "http://172.17.0.1:8081"


@patch("app.utils.get_core_host_ip", return_value="172.17.0.1")
def test_ids_component_get_http_url_no_host_system(mock_core_ip):
    """Component with no host_system should fall back to core host IP."""
    component = IdsComponent(id=1, name="sensor", role="SENSOR", port=8081)
    component.host_system = None
    assert component.get_http_url() == "http://172.17.0.1:8081"
