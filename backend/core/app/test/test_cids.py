import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.cids_deployment import deploy_docker_compose
from app.docker import start_docker_container
from app.models.ids_system import IdsSystem, CidsSystem
from app.models.ids_tool import IdsTool
from app.models.ids_component import IdsComponent
from app.models.configuration import Configuration
from app.models.docker_host_system import DockerHostSystem

# Import DatasetType to ensure models are registered correctly avoid SA error
import app.models.dataset_types


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_ids_tool():
    tool = MagicMock(spec=IdsTool)
    tool.deployment_type = "DOCKER_COMPOSE"
    tool.image_name = "test-image"
    tool.image_tag = "latest"
    return tool


@pytest.fixture
def mock_ids_container():
    container = MagicMock(spec=IdsSystem)
    container.id = 1
    container.name = "test-cids"
    container.port = 8080
    container.host_system = MagicMock(spec=DockerHostSystem)
    container.host_system.host = "localhost"
    container.host_system.name = "localhost"
    # Return tuple for unpacking
    container.host_system.get_host_and_docker_port.return_value = ("localhost", 2375)
    container.components = []
    return container


@pytest.fixture
def mock_config():
    config = MagicMock(spec=Configuration)
    config.read_content = AsyncMock(
        return_value=b"services:\n  sensor:\n    image: im\n  aggregator:\n    image: im"
    )
    return config


@pytest.mark.asyncio
async def test_deploy_docker_compose(
    mock_ids_container, mock_ids_tool, mock_config, mock_db_session
):
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        # Mock DockerClient and its compose attribute
        with patch("app.cids_deployment.DockerClient") as MockDockerClient:
            mock_client = MagicMock()
            MockDockerClient.return_value = mock_client

            # Mock compose.ps() return values
            # Need to mimic python_on_whales container objects
            container1 = MagicMock()
            container1.name = "bicep_cids_1_sensor_1"
            container1.network_settings.ports = {"80/tcp": [{"HostPort": "3000"}]}

            container2 = MagicMock()
            container2.name = "bicep_cids_1_aggregator_1"
            container2.network_settings.ports = {}

            mock_client.compose.ps.return_value = [container1, container2]

            async def get_host_mock(session, id):
                host = MagicMock(spec=DockerHostSystem)
                host.id = id
                host.name = "localhost"
                host.host = "localhost"
                host.get_host_and_docker_port.return_value = ("localhost", 2375)
                return host

            with patch("app.cids_deployment.get_host_by_id", side_effect=get_host_mock):
                await deploy_docker_compose(
                    mock_ids_container,
                    mock_ids_tool,
                    mock_config,
                    None,
                    mock_db_session,
                    None,
                )

        # Verify asyncio.to_thread called (for compose up)
        assert mock_to_thread.called

        # Verify DockerClient initialization
        MockDockerClient.assert_called()

        # Verify DB additions
        assert mock_db_session.add.call_count == 2


@pytest.mark.asyncio
async def test_start_docker_container_routing(
    mock_ids_container, mock_ids_tool, mock_config, mock_db_session
):
    # Patch the function where it is DEFINED, so that when docker.py imports it, it gets the mock
    with patch("app.cids_deployment.start_cids_deployment") as mock_cids_deploy:
        mock_cids_deploy.return_value = None

        await start_docker_container(
            mock_ids_container, mock_ids_tool, mock_config, None, mock_db_session
        )

        mock_cids_deploy.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_docker_container_normal(
    mock_ids_container, mock_config, mock_db_session
):
    normal_tool = MagicMock(spec=IdsTool)
    normal_tool.deployment_type = "SINGLE_CONTAINER"
    normal_tool.image_name = "test"
    normal_tool.image_tag = "latest"

    with patch("app.docker.run_container_async") as mock_run:
        mock_run.return_value = None
        with patch("app.docker.check_container_health") as mock_health:
            mock_health.return_value = True
            with patch("app.docker.inject_config") as mock_inject:

                await start_docker_container(
                    mock_ids_container, normal_tool, mock_config, None, mock_db_session
                )

                mock_run.assert_awaited_once()


def test_ids_container_url_cids():
    # Test valid CIDS sensor URL
    container = CidsSystem()
    container.port = 8080
    container.host_system = MagicMock()
    container.host_system.host = "remote-host"
    container.host_system.name = "remote"

    comp1 = IdsComponent(role="AGGREGATOR", port=9000, name="agg")
    comp2 = IdsComponent(role="SENSOR", port=3000, name="sensor")
    container.components = [comp1, comp2]

    url = container.get_container_http_url()
    assert url == "http://remote-host:3000"


def test_ids_container_url_normal():
    # Test normal container URL
    container = IdsSystem()
    container.port = 8080
    container.host_system = MagicMock()
    container.host_system.host = "localhost"
    container.host_system.name = "localhost"
    container.components = []

    with patch("app.models.ids_system.get_core_host_ip", return_value="127.0.0.1"):
        url = container.get_container_http_url()
        assert url == "http://127.0.0.1:8080"


@pytest.mark.asyncio
async def test_split_deployment(
    mock_ids_container, mock_ids_tool, mock_config, mock_db_session
):
    from app.validation.models import CidsServiceConfig

    # Mock Configuration Content
    mock_config.read_content = AsyncMock(
        return_value=b"services:\n  sensor:\n    image: sensor\n  aggregator:\n    image: aggregator\n"
    )

    # Mock CIDS Configurations (User assignments)
    cids_configs = [
        CidsServiceConfig(service_name="sensor", host_system_id=1, count=1),
        CidsServiceConfig(service_name="aggregator", host_system_id=2, count=1),
    ]

    # Mock DB Host retrieval
    async def get_host_side_effect(session, host_id):
        host = MagicMock(spec=DockerHostSystem)
        host.id = host_id
        host.name = f"Host-{host_id}"
        host.host = "localhost" if host_id == 1 else "192.168.1.100"
        host.get_host_and_docker_port.return_value = (host.host, 2375)
        return host

    with patch("app.cids_deployment.get_host_by_id", side_effect=get_host_side_effect):
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            with patch("app.cids_deployment.DockerClient") as MockDockerClient:
                mock_client = MagicMock()
                mock_client.compose.ps.return_value = []
                # Return same client for simplicity, or different ones based on call args
                MockDockerClient.return_value = mock_client

                # Exec
                await deploy_docker_compose(
                    mock_ids_container,
                    mock_ids_tool,
                    mock_config,
                    None,
                    mock_db_session,
                    cids_configs,
                )

                # Verify: Expect 2 DockerClient initializations (one for each host)
                assert MockDockerClient.call_count == 2

                # Check args for the remote host
                # The second host is 192.168.1.100
                calls = MockDockerClient.call_args_list
                # Depending on dict iteration, one of them should have host="tcp://..."
                has_remote_call = any(
                    "tcp://192.168.1.100:2375" == c.kwargs.get("host") for c in calls
                )
                assert has_remote_call
