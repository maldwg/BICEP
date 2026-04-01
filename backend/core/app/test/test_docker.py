import pytest
from docker import DockerClient
from app.test.fixtures import *
from unittest.mock import patch, MagicMock, AsyncMock
from app.deployment.deployment_plugins.docker import (
    get_docker_client,
    start_docker_container,
    inject_config,
    inject_ruleset,
    remove_docker_container,
    check_container_health
)

@pytest.fixture
def mock_database():
    mock_db = MagicMock()
    mock_db.Base = MagicMock()
    mock_db.SessionLocal = MagicMock()
    return mock_db

@pytest.fixture
def mock_client():
    return MagicMock(spec=DockerClient)

@pytest.fixture
def mock_host_system():
    return MagicMock()

@pytest.fixture
def mock_ids_container():
    return MagicMock()

@pytest.fixture
def mock_ids_tool():
    tool = MagicMock()
    tool.deployment_type = "SINGLE_CONTAINER"
    return tool

@pytest.fixture
def mock_config():
    return MagicMock()

@pytest.fixture
def mock_ruleset():
    return MagicMock()

@pytest.fixture
def mock_container():
    return MagicMock()

@patch("docker.DockerClient")
@patch("app.utils.get_core_host_ip")
def test_get_docker_client(mock_get_core_host, mock_docker_client, mock_client, mock_host_system):
    mock_get_core_host.return_value = "127.0.0.1"
    mock_docker_client.return_value = mock_client

    mock_host_system.name = "CoreHost"
    mock_host_system.host = "localhost"
    mock_host_system.docker_port = 2375
    get_host_and_docker_port_mock = MagicMock()
    get_host_and_docker_port_mock.return_value = (mock_host_system.host, mock_host_system.docker_port)
    mock_host_system.get_host_and_docker_port = get_host_and_docker_port_mock

    client = get_docker_client(mock_host_system)
    assert client == mock_client

@pytest.mark.asyncio
@patch("app.deployment.deployment_plugins.docker.get_docker_client")
@patch("app.deployment.deployment_plugins.docker.run_container_async")
@patch("app.deployment.deployment_plugins.docker.check_container_health")
@patch("app.deployment.deployment_plugins.docker.inject_config")
@patch("app.deployment.deployment_plugins.docker.inject_ruleset")
async def test_start_docker_container(
    mock_inject_ruleset, mock_inject_config, mock_check_health, mock_run, mock_get_client, mock_ids_container, mock_ids_tool, mock_config, mock_ruleset, mock_client
):
    mock_get_client.return_value = mock_client
    mock_check_health.return_value = True

    await start_docker_container(mock_ids_container, mock_ids_tool, mock_config, mock_ruleset)

    mock_run.assert_called_once()
    mock_check_health.assert_called_once()
    mock_inject_config.assert_called_once()
    mock_inject_ruleset.assert_called_once()

@pytest.mark.asyncio
@patch("app.deployment.deployment_plugins.docker.httpx.AsyncClient")
async def test_inject_config(mock_httpx_client, mock_ids_container, db_session_fixture: DatabaseSessionFixture):
    mock_config = await db_session_fixture.get_configuration_model()
    mock_response = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value.post.return_value = mock_response
    mock_response.status_code = 200

    response = await inject_config(mock_ids_container, mock_config)

    assert response == mock_response

@pytest.mark.asyncio
@patch("docker.DockerClient")
@patch("app.models.docker_host_system.DockerHostSystem.get_host_and_docker_port")
async def test_remove_docker_container(mock_get_host_and_port,mock_docker_client, mock_client, mock_container, mock_ids_container):
    mock_docker_client.return_value = mock_client
    mock_client.containers.get.return_value = mock_container
    
    mock_get_host_and_port.return_value = ("localhost", 2375)
    mock_host_system = MagicMock()
    mock_host_system.get_host_and_docker_port = mock_get_host_and_port
    mock_ids_container.host_system = mock_host_system

    await remove_docker_container(mock_ids_container)

    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()

@pytest.mark.asyncio
@patch("app.deployment.deployment_plugins.docker.httpx.AsyncClient")
async def test_check_container_health(mock_httpx_client, mock_ids_container):
    mock_response = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value.get.return_value = mock_response
    mock_response.status_code = 200

    result = await check_container_health(mock_ids_container)

    assert result is True
