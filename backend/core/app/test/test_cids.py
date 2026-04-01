import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.deployment import deploy_ids
from app.deployment.deployment_plugins.docker import start_docker_container
from app.deployment.deployment_plugins.docker_compose import deploy_docker_compose
from app.deployment.deployment_plugins.docker_compose_support.host_operations import (
    ComposeHostOperations,
)
from app.deployment.deployment_plugins.docker_compose_support.spec import (
    ComposeProjectPaths,
)
from app.models.ids_system import IdsSystem, CidsSystem
from app.models.ids_tool import IdsTool
from app.models.ids_component import IdsComponent
from app.models.configuration import Configuration
from app.models.docker_host_system import DockerHostSystem

# Import DatasetType to ensure models are registered correctly avoid SA error
import app.models.dataset_types


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


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
        with patch("app.deployment.deployment_plugins.docker_compose.DockerClient") as MockDockerClient:
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

            with patch(
                "app.deployment.deployment_plugins.docker_compose.get_host_by_id",
                side_effect=get_host_mock,
            ):
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
async def test_deploy_ids_routes_to_compose_plugin(
    mock_ids_container, mock_ids_tool, mock_config, mock_db_session
):
    with patch("app.deployment.common.get_deployment_plugin") as mock_get_plugin:
        mock_plugin = MagicMock()
        mock_plugin.deploy = AsyncMock()
        mock_get_plugin.return_value = mock_plugin

        await deploy_ids(
            mock_ids_container,
            mock_ids_tool,
            mock_config,
            None,
            mock_db_session,
        )

        mock_get_plugin.assert_called_once_with(mock_ids_tool.deployment_type)
        mock_plugin.deploy.assert_awaited_once()


@pytest.mark.asyncio
async def test_compose_teardown_project_offloads_blocking_work():
    host_operations = ComposeHostOperations(
        docker_client_cls=MagicMock(),
        docker_sdk_module=MagicMock(),
        ids_component_cls=IdsComponent,
        logger=MagicMock(),
        get_core_url=MagicMock(return_value="http://core"),
    )
    host_system = MagicMock(spec=DockerHostSystem)
    paths = ComposeProjectPaths(container_id=1, host_name="localhost")

    with patch(
        "app.deployment.deployment_plugins.docker_compose_support.host_operations.asyncio.to_thread",
        new_callable=AsyncMock,
    ) as mock_to_thread:
        with patch.object(
            host_operations,
            "_remove_local_work_dir",
            new_callable=AsyncMock,
        ) as mock_remove_local_work_dir:
            await host_operations.teardown_project(
                host_system=host_system,
                components=[],
                paths=paths,
            )

    mock_to_thread.assert_awaited_once()
    assert mock_to_thread.await_args.args[1:] == (host_system, [], paths)
    mock_remove_local_work_dir.assert_awaited_once_with(paths.work_dir)


@pytest.mark.asyncio
async def test_start_docker_container_normal(
    mock_ids_container, mock_config, mock_db_session
):
    normal_tool = MagicMock(spec=IdsTool)
    normal_tool.deployment_type = "SINGLE_CONTAINER"
    normal_tool.image_name = "test"
    normal_tool.image_tag = "latest"

    with patch("app.deployment.deployment_plugins.docker.get_docker_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()
        with patch("app.deployment.deployment_plugins.docker.run_container_async") as mock_run:
            mock_run.return_value = None
            with patch("app.deployment.deployment_plugins.docker.check_container_health") as mock_health:
                mock_health.return_value = True
                with patch("app.deployment.deployment_plugins.docker.inject_config") as mock_inject:

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

    with patch(
        "app.deployment.deployment_plugins.docker_compose.get_host_by_id",
        side_effect=get_host_side_effect,
    ):
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            with patch("app.deployment.deployment_plugins.docker_compose.DockerClient") as MockDockerClient:
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


@pytest.mark.asyncio
async def test_deploy_docker_compose_rejects_wrong_runtime_config_extension(
    mock_ids_container, mock_ids_tool, mock_db_session
):
    from app.validation.models import CidsServiceConfig

    compose_config = MagicMock(spec=Configuration)
    compose_config.read_content = AsyncMock(
        return_value=b"""
services:
  detector:
    image: detector
    labels:
      - "bicep.config.mount=/app/config.yaml"
"""
    )

    runtime_config = MagicMock(spec=Configuration)
    runtime_config.id = 99
    runtime_config.name = "detector-config.txt"
    runtime_config.file_path = "/tmp/detector-config.txt"

    cids_configs = [
        CidsServiceConfig(
            service_name="detector",
            host_system_id=1,
            count=1,
            runtime_configuration_id=99,
        )
    ]

    with patch(
        "app.deployment.deployment_plugins.docker_compose.get_config_by_id",
        AsyncMock(return_value=runtime_config),
    ):
        with pytest.raises(ValueError, match="expects a config ending in '.yaml'"):
            await deploy_docker_compose(
                mock_ids_container,
                mock_ids_tool,
                compose_config,
                None,
                mock_db_session,
                cids_configs,
            )
