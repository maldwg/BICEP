import pytest
from docker import DockerClient
from unittest.mock import patch, MagicMock, AsyncMock
from ..docker import (
    get_docker_client,
    start_docker_container,
    inject_config,
    inject_ruleset,
    remove_docker_container,
    check_container_health,
    calculate_memory_usage,
    calculate_cpu_usage
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
    return MagicMock()

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
@patch("app.docker.get_core_host")
def test_get_docker_client(mock_get_core_host, mock_docker_client, mock_client, mock_host_system):
    mock_get_core_host.return_value = "127.0.0.1"
    mock_docker_client.return_value = mock_client

    mock_host_system.name = "CoreHost"
    mock_host_system.host = "localhost"
    mock_host_system.docker_port = 2375

    client = get_docker_client(mock_host_system)
    assert client == mock_client

@pytest.mark.asyncio
@patch("app.docker.get_docker_client")
@patch("app.docker.run_container_async")
@patch("app.docker.check_container_health")
@patch("app.docker.inject_config")
@patch("app.docker.inject_ruleset")
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
@patch("app.docker.httpx.AsyncClient")
async def test_inject_config(mock_httpx_client, mock_ids_container, mock_config):
    mock_response = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value.post.return_value = mock_response
    mock_response.status_code = 200

    response = await inject_config(mock_ids_container, mock_config)

    assert response == mock_response

@pytest.mark.asyncio
@patch("docker.DockerClient")
async def test_remove_docker_container(mock_docker_client, mock_client, mock_container, mock_ids_container):
    mock_docker_client.return_value = mock_client
    mock_client.containers.get.return_value = mock_container

    await remove_docker_container(mock_ids_container)

    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()

@pytest.mark.asyncio
@patch("app.docker.httpx.AsyncClient")
async def test_check_container_health(mock_httpx_client, mock_ids_container):
    mock_response = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value.get.return_value = mock_response
    mock_response.status_code = 200

    result = await check_container_health(mock_ids_container)

    assert result is True

@pytest.mark.asyncio
async def test_calculate_memory_usage():
    stats = {"memory_stats": {"usage": 10485760}}  # 10MB
    memory_usage = await calculate_memory_usage(stats)
    assert memory_usage == 10.0

@pytest.mark.asyncio
async def test_calculate_cpu_usage():
    stats = {
        "cpu_stats": {
            "cpu_usage": {
                "total_usage": 20000000,
                "percpu_usage": [10000000, 10000000]
            },
            "system_cpu_usage": 100000000
        },
        "precpu_stats": {
            "cpu_usage": {
                "total_usage": 10000000,
            },
            "system_cpu_usage": 50000000,
            "online_cpus": 2
        }
    }
    cpu_usage = await calculate_cpu_usage(stats)
    assert round(cpu_usage, 2) == 20.0
