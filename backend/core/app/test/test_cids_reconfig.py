import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.ids_system import CidsSystem
from app.models.ids_component import IdsComponent
from app.models.docker_host_system import DockerHostSystem
from app.utils import STATUS


@pytest.fixture
def mock_host_system():
    host = MagicMock(spec=DockerHostSystem)
    host.id = 1
    host.name = "TestHost"
    host.host = "192.168.1.100"
    host.docker_port = 2375
    return host


@pytest.fixture
def mock_components(mock_host_system):
    sensor = MagicMock(spec=IdsComponent)
    sensor.id = 1
    sensor.name = "bicep_cids_1_sensor"
    sensor.role = "SENSOR"
    sensor.port = 8081
    sensor.host_system = mock_host_system
    sensor.get_http_url.return_value = "http://192.168.1.100:8081"

    aggregator = MagicMock(spec=IdsComponent)
    aggregator.id = 2
    aggregator.name = "bicep_cids_1_aggregator"
    aggregator.role = "AGGREGATOR"
    aggregator.port = 8082
    aggregator.host_system = mock_host_system
    aggregator.get_http_url.return_value = "http://192.168.1.100:8082"

    return [sensor, aggregator]


@pytest.fixture
def mock_component_no_port(mock_host_system):
    """A component without an exposed port (e.g. internal-only service)."""
    comp = MagicMock(spec=IdsComponent)
    comp.id = 3
    comp.name = "bicep_cids_1_internal"
    comp.role = "INTERNAL"
    comp.port = None
    comp.host_system = mock_host_system
    return comp


@pytest.fixture
def cids_system(mock_host_system, mock_components):
    cids = CidsSystem.__new__(CidsSystem)
    cids.id = 1
    cids.name = "Test CIDS"
    cids.port = 8080
    cids.status = STATUS.IDLE.value
    cids.host_system = mock_host_system
    cids.components = mock_components
    return cids


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
@patch("app.models.ids_system.select")
@patch("app.docker.inject_config_to_url", new_callable=AsyncMock)
@patch("app.docker.restart_docker_container", new_callable=AsyncMock)
async def test_cids_update_config_propagates_to_all_components(
    mock_restart, mock_inject, mock_select, cids_system, mock_config
):
    """update_config should inject config to every component with a port and then restart all."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_config
    db.execute.return_value = mock_result

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
@patch("app.models.ids_system.select")
@patch("app.docker.inject_config_to_url", new_callable=AsyncMock)
@patch("app.docker.restart_docker_container", new_callable=AsyncMock)
async def test_cids_update_config_skips_components_without_port(
    mock_restart,
    mock_inject,
    mock_select,
    cids_system,
    mock_config,
    mock_component_no_port,
):
    """Components without a port should not receive config injection."""
    cids_system.components.append(mock_component_no_port)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_config
    db.execute.return_value = mock_result

    await cids_system.update_config(db, config_id=10)

    # Only 2 components have ports (sensor + aggregator), not the internal one
    assert mock_inject.call_count == 2
    # But all 3 components get restarted
    assert mock_restart.call_count == 3


@pytest.mark.asyncio
@patch("app.models.ids_system.select")
@patch("app.docker.inject_config_to_url", new_callable=AsyncMock)
@patch("app.docker.restart_docker_container", new_callable=AsyncMock)
async def test_cids_update_config_no_op_for_missing_config(
    mock_restart, mock_inject, mock_select, cids_system
):
    """If the config ID doesn't exist, nothing should happen."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    await cids_system.update_config(db, config_id=999)

    mock_inject.assert_not_called()
    mock_restart.assert_not_called()


# ==================== update_ruleset tests ====================


@pytest.mark.asyncio
@patch("app.models.ids_system.select")
@patch("app.docker.inject_ruleset_to_url", new_callable=AsyncMock)
@patch("app.docker.restart_docker_container", new_callable=AsyncMock)
async def test_cids_update_ruleset_propagates_to_all_components(
    mock_restart, mock_inject_ruleset, mock_select, cids_system, mock_ruleset
):
    """update_ruleset should inject ruleset to every component with a port and restart all."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_ruleset
    db.execute.return_value = mock_result

    await cids_system.update_ruleset(db, ruleset_id=20)

    assert mock_inject_ruleset.call_count == 2
    mock_inject_ruleset.assert_any_call("http://192.168.1.100:8081", mock_ruleset)
    mock_inject_ruleset.assert_any_call("http://192.168.1.100:8082", mock_ruleset)

    assert mock_restart.call_count == 2


@pytest.mark.asyncio
@patch("app.models.ids_system.select")
@patch("app.docker.inject_ruleset_to_url", new_callable=AsyncMock)
@patch("app.docker.restart_docker_container", new_callable=AsyncMock)
async def test_cids_update_ruleset_no_op_for_missing_ruleset(
    mock_restart, mock_inject_ruleset, mock_select, cids_system
):
    """If the ruleset ID doesn't exist, nothing should happen."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    await cids_system.update_ruleset(db, ruleset_id=999)

    mock_inject_ruleset.assert_not_called()
    mock_restart.assert_not_called()


# ==================== restart_docker_container tests ====================


@pytest.mark.asyncio
@patch("app.docker.get_docker_client")
async def test_restart_docker_container_calls_docker_api(
    mock_get_client, mock_components
):
    from app.docker import restart_docker_container

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
