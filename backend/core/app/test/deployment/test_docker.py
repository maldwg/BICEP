import pytest
from docker import DockerClient
from app.test.fixtures import *
from unittest.mock import patch, MagicMock, AsyncMock
from app.deployment.deployment_plugins.docker import (
    DOCKER_CONTROL_CLIENT_TIMEOUT,
    ensure_image_present_blocking,
    get_docker_client,
    start_docker_container,
    inject_config,
    inject_ruleset,
    remove_docker_container,
    check_container_health,
    restart_docker_container,
    run_container_async,
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
def test_get_docker_client_core_host_uses_socket(mock_docker_client, mock_client, mock_host_system):
    mock_docker_client.return_value = mock_client
    mock_host_system.is_core_host.return_value = True

    client = get_docker_client(mock_host_system)

    assert client == mock_client
    called_url = mock_docker_client.call_args[1]["base_url"]
    assert called_url.startswith("unix://")


@patch("docker.DockerClient")
def test_get_docker_client_remote_host_uses_tcp(mock_docker_client, mock_client, mock_host_system):
    mock_docker_client.return_value = mock_client
    mock_host_system.is_core_host.return_value = False
    mock_host_system.get_host_and_docker_port.return_value = ("10.0.0.5", 2376)

    client = get_docker_client(mock_host_system)

    assert client == mock_client
    called_url = mock_docker_client.call_args[1]["base_url"]
    assert called_url == "tcp://10.0.0.5:2376"

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
    mock_host_system.is_core_host.return_value = False
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


@pytest.mark.asyncio
@patch("app.deployment.deployment_plugins.docker.get_docker_client")
async def test_restart_docker_container_calls_docker_api(
    mock_get_client, mock_container
):
    mock_docker_client = MagicMock()
    mock_docker_client.containers.get.return_value = mock_container
    mock_get_client.return_value = mock_docker_client

    component = MagicMock()
    component.name = "sensor"
    component.host_system = MagicMock()

    await restart_docker_container(component)

    mock_get_client.assert_called_once_with(
        component.host_system,
        timeout=DOCKER_CONTROL_CLIENT_TIMEOUT,
    )
    mock_docker_client.containers.get.assert_called_once_with(component.name)
    mock_container.restart.assert_called_once_with(timeout=10)
    mock_docker_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_run_container_async_pulls_image_before_create():
    client = MagicMock()
    created_container = MagicMock()
    client.containers.create.return_value = created_container

    ids_tool = MagicMock()
    ids_tool.image_name = "ghcr.io/example/ids"
    ids_tool.image_tag = "1.2.3"

    container = MagicMock()
    container.name = "ids-1"
    container.port = 8080

    async def run_immediately(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch(
        "app.deployment.deployment_plugins.docker.asyncio.to_thread",
        new=AsyncMock(side_effect=run_immediately),
    ):
        await run_container_async(client, ids_tool, container, "http://core")

    client.images.pull.assert_called_once_with(
        repository="ghcr.io/example/ids",
        tag="1.2.3",
    )
    client.containers.create.assert_called_once()
    created_container.start.assert_called_once()


def test_ensure_image_present_blocking_uses_local_image_if_pull_fails():
    client = MagicMock()
    client.images.pull.side_effect = Exception("registry down")
    client.images.get.return_value = MagicMock()

    ensure_image_present_blocking(client, "ghcr.io/example/ids:1.2.3")

    client.images.pull.assert_called_once_with(
        repository="ghcr.io/example/ids",
        tag="1.2.3",
    )
    client.images.get.assert_called_once_with("ghcr.io/example/ids:1.2.3")
