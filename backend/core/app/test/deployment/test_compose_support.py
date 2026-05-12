from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from python_on_whales.exceptions import DockerException

from app.deployment.deployment_plugins.docker_compose import (
    DockerComposeDeploymentPlugin,
    _build_compose_services,
    start_cids_deployment,
)
from app.deployment.deployment_plugins.docker_compose_support.availability import (
    ComposeAvailabilityChecker,
)
from app.deployment.deployment_plugins.docker_compose_support.deployment import (
    ComposeDeploymentService,
)
from app.deployment.deployment_plugins.docker_compose_support.host_operations import (
    ComposeHostOperations,
)
from app.deployment.deployment_plugins.docker_compose_support.spec import (
    ComposeProjectPaths,
    ComposeSpecManager,
    PreparedComposeHostDeployment,
)
from app.models.configuration import Configuration
from app.models.ids_component import IdsComponent
from app.models.ids_system import IdsSystem
import app.models.dataset_types


class FakeAsyncClient:
    def __init__(self, responses, requested_urls):
        self._responses = responses
        self._requested_urls = requested_urls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        self._requested_urls.append(url)
        response = MagicMock()
        value = self._responses[url]
        if isinstance(value, Exception):
            raise value
        response.status_code = value
        return response


@pytest.fixture
def compose_spec_manager():
    return ComposeSpecManager(
        get_config_by_id=AsyncMock(),
        get_core_url=MagicMock(return_value="http://core"),
    )


def test_build_compose_services_returns_deployment_and_availability_objects():
    deployment_service, availability_checker = _build_compose_services()

    assert isinstance(deployment_service, ComposeDeploymentService)
    assert isinstance(availability_checker, ComposeAvailabilityChecker)


@pytest.mark.asyncio
async def test_start_cids_deployment_builds_context_and_delegates():
    ids_container = MagicMock()
    ids_tool = MagicMock()
    config = MagicMock()
    ruleset = MagicMock()
    db_session = AsyncMock()

    with patch(
        "app.deployment.deployment_plugins.docker_compose.DockerComposeDeploymentPlugin.deploy",
        new_callable=AsyncMock,
    ) as mock_deploy:
        await start_cids_deployment(
            ids_container,
            ids_tool,
            config,
            ruleset,
            db_session,
            cids_configurations=["sensor"],
            env_vars={"MODE": "test"},
        )

    context = mock_deploy.await_args.args[0]
    assert context.ids_system is ids_container
    assert context.ids_tool is ids_tool
    assert context.config is config
    assert context.ruleset is ruleset
    assert context.db_session is db_session
    assert context.cids_configurations == ["sensor"]
    assert context.env_vars == {"MODE": "test"}


@pytest.mark.asyncio
async def test_compose_plugin_methods_delegate_to_helpers():
    plugin = DockerComposeDeploymentPlugin()
    ids_system = MagicMock()
    configuration = MagicMock()
    ruleset = MagicMock()

    with patch(
        "app.deployment.deployment_plugins.docker_compose.inject_single_container_config",
        new_callable=AsyncMock,
    ) as mock_inject_config:
        await plugin.inject_config(ids_system, configuration)
    mock_inject_config.assert_awaited_once_with(ids_system, configuration)

    with patch(
        "app.deployment.deployment_plugins.docker_compose.inject_single_container_ruleset",
        new_callable=AsyncMock,
    ) as mock_inject_ruleset:
        await plugin.inject_ruleset(ids_system, ruleset)
    mock_inject_ruleset.assert_awaited_once_with(ids_system, ruleset)


@pytest.mark.asyncio
async def test_compose_plugin_start_refreshes_components():
    plugin = DockerComposeDeploymentPlugin()
    context = MagicMock()
    context.ids_system = MagicMock()
    context.ids_tool = MagicMock()
    context.config = MagicMock()
    context.ruleset = MagicMock()
    context.db_session = AsyncMock()
    context.cids_configurations = []
    context.env_vars = {}

    with patch(
        "app.deployment.deployment_plugins.docker_compose.deploy_docker_compose",
        new_callable=AsyncMock,
    ) as mock_deploy:
        await plugin.start(context)

    mock_deploy.assert_awaited_once()
    context.db_session.refresh.assert_awaited_once_with(
        context.ids_system,
        attribute_names=["components"],
    )


@pytest.mark.asyncio
async def test_compose_plugin_teardown_skips_remote_cleanup_when_already_done():
    plugin = DockerComposeDeploymentPlugin()
    ids_system = MagicMock()
    ids_system._deployment_cleanup_done = True
    ids_system.ensemble_ids = []
    ids_system.components = [MagicMock(), MagicMock()]
    ids_system.status = "active"
    ids_system.deployment_status = "deployed"
    db_session = AsyncMock()

    deployment_service = MagicMock()
    availability_checker = MagicMock()

    with patch(
        "app.deployment.deployment_plugins.docker_compose._build_compose_services",
        return_value=(deployment_service, availability_checker),
    ):
        await plugin.teardown(ids_system, db_session)

    deployment_service.teardown.assert_not_called()
    assert db_session.delete.await_count == 2
    assert ids_system.status == "idle"
    assert ids_system.deployment_status == "deleted"
    db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_compose_plugin_is_available_delegates_to_checker():
    plugin = DockerComposeDeploymentPlugin()
    ids_system = MagicMock()
    availability_checker = MagicMock()
    availability_checker.is_available = AsyncMock(return_value=True)

    with patch(
        "app.deployment.deployment_plugins.docker_compose._build_compose_services",
        return_value=(MagicMock(), availability_checker),
    ):
        result = await plugin.is_available(ids_system)

    assert result is True
    availability_checker.is_available.assert_awaited_once_with(ids_system)


@pytest.mark.asyncio
async def test_compose_plugin_update_components_redeploys_only_changed_services():
    plugin = DockerComposeDeploymentPlugin()
    deployment_service = MagicMock()
    deployment_service.redeploy_services = AsyncMock()
    ids_system = SimpleNamespace(
        configuration_id=9,
        ruleset_id=None,
        host_system_id=1,
        components=[
            SimpleNamespace(
                host_system_id=1,
                service_name="sensor",
                count=3,
                runtime_configuration_id=5,
            ),
            SimpleNamespace(
                host_system_id=1,
                service_name="aggregator",
                count=1,
                runtime_configuration_id=None,
            ),
        ],
    )
    db_session = AsyncMock()
    config = MagicMock()

    with patch(
        "app.deployment.deployment_plugins.docker_compose._build_compose_services",
        return_value=(deployment_service, MagicMock()),
    ), patch(
        "app.deployment.deployment_plugins.docker_compose.load_configuration",
        new=AsyncMock(return_value=config),
    ):
        await plugin.update_components(
            ids_system,
            db_session,
            [
                SimpleNamespace(
                    host_system_id=1,
                    service_name="sensor",
                    count=3,
                    runtime_configuration_id=5,
                )
            ],
        )

    deployment_service.redeploy_services.assert_awaited_once()
    call_kwargs = deployment_service.redeploy_services.await_args.kwargs
    assert call_kwargs["changed_service_keys"] == {(1, "sensor")}
    assert {
        (svc.host_system_id, svc.service_name)
        for svc in call_kwargs["cids_configurations"]
    } == {(1, "sensor"), (1, "aggregator")}


def test_spec_manager_prepare_host_deployment_customizes_sensor_service(compose_spec_manager):
    runtime_config = MagicMock()
    runtime_config.file_path = "/tmp/runtime.yml"

    compose_data = {
        "services": {
            "sensor": {
                "image": "sensor",
                "labels": [
                    "bicep.config.mount=/app/config.yaml",
                    "bicep.sensor=true",
                ],
                "volumes": ["/old/file:/app/config.yaml"],
                "environment": ["FOO=bar"],
                "container_name": "sensor",
            }
        }
    }
    services = [SimpleNamespace(service_name="sensor", count=1)]
    ids_container = SimpleNamespace(id=5, port=8080)
    host_system = SimpleNamespace(name="Host A")

    deployment = compose_spec_manager.prepare_host_deployment(
        compose_data=compose_data,
        services=services,
        ids_container=ids_container,
        host_system=host_system,
        service_runtime_configs={"sensor": runtime_config},
    )

    sensor_config = deployment.compose_data["services"]["sensor"]
    assert deployment.paths.project_name == "bicep_cids_5_host_a"
    assert sensor_config["environment"]["FOO"] == "bar"
    assert sensor_config["environment"]["PORT"] == "8080"
    assert sensor_config["environment"]["CORE_URL"] == "http://core"
    assert sensor_config["environment"]["TZ"] == "UTC"
    assert sensor_config["volumes"] == [
        f"{next(iter(deployment.runtime_config_files))}:/app/config.yaml"
    ]


@pytest.mark.asyncio
async def test_spec_manager_resolve_runtime_configs_supports_yaml_alias(compose_spec_manager):
    runtime_config = MagicMock()
    runtime_config.file_path = "/tmp/runtime.yml"
    runtime_config.name = "runtime.yml"
    compose_spec_manager._get_config_by_id.return_value = runtime_config

    configs = await compose_spec_manager.resolve_service_runtime_configs(
        AsyncMock(),
        {
            "services": {
                "sensor": {
                    "labels": {"bicep.config.mount": "/app/config.yaml"},
                }
            }
        },
        [SimpleNamespace(service_name="sensor", runtime_configuration_id=1)],
    )

    assert configs == {"sensor": runtime_config}


@pytest.mark.asyncio
async def test_spec_manager_resolve_runtime_configs_requires_mount_label(compose_spec_manager):
    runtime_config = MagicMock()
    runtime_config.file_path = "/tmp/runtime.yaml"
    runtime_config.name = "runtime.yaml"
    compose_spec_manager._get_config_by_id.return_value = runtime_config

    with pytest.raises(ValueError, match="bicep.config.mount label"):
        await compose_spec_manager.resolve_service_runtime_configs(
            AsyncMock(),
            {"services": {"sensor": {"labels": {}}}},
            [SimpleNamespace(service_name="sensor", runtime_configuration_id=1)],
        )


@pytest.mark.asyncio
async def test_spec_manager_write_deployment_files_writes_ruleset_and_runtime_config(
    compose_spec_manager, tmp_path
):
    runtime_config = MagicMock(spec=Configuration)
    runtime_config.read_content = AsyncMock(return_value="sensor-config")
    ruleset = MagicMock(spec=Configuration)
    ruleset.read_content = AsyncMock(return_value=b"alert any")

    deployment = PreparedComposeHostDeployment(
        host_system=MagicMock(),
        services=[],
        compose_data={"services": {"sensor": {"image": "sensor"}}},
        runtime_config_files={str(tmp_path / "sensor.yaml"): runtime_config},
        paths=SimpleNamespace(
            compose_file_path=str(tmp_path / "docker-compose.yaml"),
            work_dir=str(tmp_path),
        ),
    )

    await compose_spec_manager.write_deployment_files(deployment, ruleset)

    assert (tmp_path / "docker-compose.yaml").exists()
    assert (tmp_path / "rules.yaml").read_bytes() == b"alert any"
    assert (tmp_path / "sensor.yaml").read_text() == "sensor-config"


@patch("os.path.exists", return_value=True)
def test_get_docker_host_url_core_host_returns_unix_socket(mock_exists):
    host_operations = ComposeHostOperations(
        docker_client_cls=MagicMock(),
        docker_sdk_module=MagicMock(),
        ids_component_cls=MagicMock(),
        logger=MagicMock(),
        get_core_url=MagicMock(),
    )
    host_system = SimpleNamespace(is_core_host=lambda: True)
    url = host_operations.get_docker_host_url(host_system)
    assert url.startswith("unix://")


@patch("os.path.exists", return_value=False)
def test_get_docker_host_url_core_host_falls_back_to_tcp_when_no_socket(mock_exists):
    host_operations = ComposeHostOperations(
        docker_client_cls=MagicMock(),
        docker_sdk_module=MagicMock(),
        ids_component_cls=MagicMock(),
        logger=MagicMock(),
        get_core_url=MagicMock(),
    )
    host_system = SimpleNamespace(
        is_core_host=lambda: True,
        get_host_and_docker_port=lambda: ("172.17.0.1", 2375),
    )
    url = host_operations.get_docker_host_url(host_system)
    assert url == "tcp://172.17.0.1:2375"


def test_get_docker_host_url_remote_host_returns_tcp():
    host_operations = ComposeHostOperations(
        docker_client_cls=MagicMock(),
        docker_sdk_module=MagicMock(),
        ids_component_cls=MagicMock(),
        logger=MagicMock(),
        get_core_url=MagicMock(),
    )
    host_system = SimpleNamespace(
        is_core_host=lambda: False,
        get_host_and_docker_port=lambda: ("10.0.0.5", 2376),
    )
    url = host_operations.get_docker_host_url(host_system)
    assert url == "tcp://10.0.0.5:2376"


def test_host_operations_copy_runtime_configs_blocking_uploads_archive(tmp_path):
    docker_sdk_module = MagicMock()
    host_docker = MagicMock()
    docker_sdk_module.DockerClient.return_value = host_docker
    first_container = MagicMock()
    second_container = MagicMock()
    host_docker.containers.create.side_effect = [first_container, second_container]

    host_operations = ComposeHostOperations(
        docker_client_cls=MagicMock(),
        docker_sdk_module=docker_sdk_module,
        ids_component_cls=IdsComponent,
        logger=MagicMock(),
        get_core_url=MagicMock(return_value="http://core"),
    )

    runtime_file = tmp_path / "sensor.yaml"
    runtime_file.write_text("content")
    deployment = SimpleNamespace(
        host_system=SimpleNamespace(
            get_host_and_docker_port=lambda: ("127.0.0.1", 2375),
            is_core_host=lambda: True,
        ),
        runtime_config_files={str(runtime_file): MagicMock()},
        paths=SimpleNamespace(work_dir="/tmp/bicep_cids_1_localhost"),
    )

    host_operations._copy_runtime_configs_blocking(deployment)

    host_docker.images.pull.assert_called_once_with(
        repository="alpine",
        tag="latest",
    )
    assert host_docker.containers.create.call_count == 2
    second_container.put_archive.assert_called_once()
    host_docker.close.assert_called_once()


@pytest.mark.asyncio
async def test_host_operations_start_project_registers_components_and_scales():
    ids_component_cls = lambda **kwargs: SimpleNamespace(**kwargs)
    client = MagicMock()
    docker_sdk_module = MagicMock()
    host_docker = MagicMock()
    docker_sdk_module.DockerClient.return_value = host_docker
    container_sensor = MagicMock()
    container_sensor.name = "sensor"
    container_sensor.network_settings.ports = {"80/tcp": [{"HostPort": "3001"}]}
    container_sensor.config.labels = {
        "bicep.role": "SENSOR",
        "com.docker.compose.service": "sensor",
    }

    container_aggregator = MagicMock()
    container_aggregator.name = "aggregator-1"
    container_aggregator.network_settings.ports = {}
    container_aggregator.config.labels = {
        "com.docker.compose.service": "aggregator",
    }

    client.compose.ps.return_value = [container_sensor, container_aggregator]
    docker_client_cls = MagicMock(return_value=client)

    async def run_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    host_operations = ComposeHostOperations(
        docker_client_cls=docker_client_cls,
        docker_sdk_module=docker_sdk_module,
        ids_component_cls=ids_component_cls,
        logger=MagicMock(),
        get_core_url=MagicMock(return_value="http://core"),
    )

    deployment = SimpleNamespace(
        host_system=SimpleNamespace(
            name="Remote",
            id=5,
            is_core_host=lambda: False,
            get_host_and_docker_port=lambda: ("10.0.0.5", 2375),
        ),
        paths=SimpleNamespace(
            compose_file_path="/tmp/docker-compose.yaml",
            project_name="bicep_cids_1_remote",
        ),
        services=[SimpleNamespace(service_name="sensor", count=2)],
        compose_data={
            "services": {
                "sensor": {"image": "ghcr.io/example/sensor:1.0.0"},
                "aggregator": {"image": "ghcr.io/example/aggregator:2.0.0"},
            }
        },
    )
    ids_container = SimpleNamespace(id=1, port=8080, components=[])
    db_session = MagicMock()

    with patch(
        "app.deployment.deployment_plugins.docker_compose_support.host_operations.asyncio.to_thread",
        side_effect=run_to_thread,
    ):
        await host_operations.start_project(
            deployment=deployment,
            ids_container=ids_container,
            db_session=db_session,
            env_vars={"EXTRA": "1"},
        )

    docker_client_cls.assert_called_once_with(
        host="tcp://10.0.0.5:2375",
        compose_files=["/tmp/docker-compose.yaml"],
        compose_project_name="bicep_cids_1_remote",
    )
    client.compose.up.assert_called_once_with(
        detach=True,
        quiet=False,
        scales={"sensor": 2},
    )
    assert host_docker.images.pull.call_args_list == [
        call(repository="ghcr.io/example/sensor", tag="1.0.0"),
        call(repository="ghcr.io/example/aggregator", tag="2.0.0"),
    ]
    assert db_session.add.call_count == 2
    assert ids_container.components[0].port == 8080
    assert ids_container.components[1].role == "AGGREGATOR"


@pytest.mark.asyncio
async def test_host_operations_start_project_redeploys_only_requested_services():
    ids_component_cls = lambda **kwargs: SimpleNamespace(**kwargs)
    client = MagicMock()
    docker_sdk_module = MagicMock()
    host_docker = MagicMock()
    docker_sdk_module.DockerClient.return_value = host_docker
    container_sensor = MagicMock()
    container_sensor.name = "sensor-1"
    container_sensor.network_settings.ports = {"80/tcp": [{"HostPort": "3001"}]}
    container_sensor.config.labels = {
        "bicep.role": "SENSOR",
        "com.docker.compose.service": "sensor",
    }

    container_aggregator = MagicMock()
    container_aggregator.name = "aggregator-1"
    container_aggregator.network_settings.ports = {}
    container_aggregator.config.labels = {
        "com.docker.compose.service": "aggregator",
    }

    client.compose.ps.return_value = [container_sensor, container_aggregator]
    docker_client_cls = MagicMock(return_value=client)

    async def run_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    host_operations = ComposeHostOperations(
        docker_client_cls=docker_client_cls,
        docker_sdk_module=docker_sdk_module,
        ids_component_cls=ids_component_cls,
        logger=MagicMock(),
        get_core_url=MagicMock(return_value="http://core"),
    )

    deployment = SimpleNamespace(
        host_system=SimpleNamespace(
            name="Remote",
            id=5,
            is_core_host=lambda: False,
            get_host_and_docker_port=lambda: ("10.0.0.5", 2375),
        ),
        paths=SimpleNamespace(
            compose_file_path="/tmp/docker-compose.yaml",
            project_name="bicep_cids_1_remote",
        ),
        services=[
            SimpleNamespace(service_name="sensor", count=1),
            SimpleNamespace(service_name="aggregator", count=2),
        ],
        compose_data={
            "services": {
                "sensor": {"image": "ghcr.io/example/sensor:1.0.0"},
                "aggregator": {"image": "ghcr.io/example/aggregator:2.0.0"},
            }
        },
    )
    ids_container = SimpleNamespace(id=1, port=8080, components=[])
    db_session = MagicMock()

    with patch(
        "app.deployment.deployment_plugins.docker_compose_support.host_operations.asyncio.to_thread",
        side_effect=run_to_thread,
    ):
        await host_operations.start_project(
            deployment=deployment,
            ids_container=ids_container,
            db_session=db_session,
            services=["sensor"],
        )

    client.compose.up.assert_called_once_with(
        services=["sensor"],
        detach=True,
        quiet=False,
        scales={"sensor": 1},
        force_recreate=True,
    )
    host_docker.images.pull.assert_called_once_with(
        repository="ghcr.io/example/sensor",
        tag="1.0.0",
    )
    assert db_session.add.call_count == 1
    assert ids_container.components[0].service_name == "sensor"


@pytest.mark.asyncio
async def test_host_operations_start_project_wraps_compose_errors():
    client = MagicMock()
    client.compose.up.side_effect = DockerException("boom", 1)

    async def run_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    host_operations = ComposeHostOperations(
        docker_client_cls=MagicMock(return_value=client),
        docker_sdk_module=MagicMock(),
        ids_component_cls=IdsComponent,
        logger=MagicMock(),
        get_core_url=MagicMock(return_value="http://core"),
    )
    deployment = SimpleNamespace(
        host_system=SimpleNamespace(
            name="Remote",
            is_core_host=lambda: False,
            get_host_and_docker_port=lambda: ("10.0.0.5", 2375),
        ),
        paths=SimpleNamespace(
            compose_file_path="/tmp/docker-compose.yaml",
            project_name="bicep_cids_1_remote",
        ),
        services=[],
        compose_data={"services": {}},
    )

    with patch(
        "app.deployment.deployment_plugins.docker_compose_support.host_operations.asyncio.to_thread",
        side_effect=run_to_thread,
    ):
        with pytest.raises(Exception, match="Docker Compose failed on Remote"):
            await host_operations.start_project(
                deployment=deployment,
                ids_container=SimpleNamespace(id=1, port=8080, components=[]),
                db_session=MagicMock(),
            )


def test_host_operations_teardown_remote_project_blocking_falls_back_to_container_cleanup():
    compose_client = MagicMock()
    compose_client.compose.down.side_effect = DockerException("down failed", 1)

    fallback_docker_client = MagicMock()
    fallback_container = MagicMock()
    fallback_docker_client.containers.get.return_value = fallback_container

    cleanup_client = MagicMock()
    cleanup_client.containers.list.return_value = [MagicMock()]
    cleanup_client.networks.list.return_value = [MagicMock()]
    cleanup_client.volumes.list.return_value = [MagicMock()]

    remote_cleanup_client = MagicMock()
    cleanup_container = MagicMock()
    remote_cleanup_client.containers.create.return_value = cleanup_container

    docker_sdk_module = MagicMock()
    docker_sdk_module.DockerClient.side_effect = [
        fallback_docker_client,
        cleanup_client,
        remote_cleanup_client,
    ]
    docker_sdk_module.errors.NotFound = type("NotFound", (Exception,), {})

    host_operations = ComposeHostOperations(
        docker_client_cls=MagicMock(return_value=compose_client),
        docker_sdk_module=docker_sdk_module,
        ids_component_cls=IdsComponent,
        logger=MagicMock(),
        get_core_url=MagicMock(return_value="http://core"),
    )

    result = host_operations._teardown_remote_project_blocking(
        host_system=SimpleNamespace(
            name="Remote",
            is_core_host=lambda: False,
            get_host_and_docker_port=lambda: ("10.0.0.5", 2375),
        ),
        components=[SimpleNamespace(name="sensor")],
        paths=ComposeProjectPaths(container_id=1, host_name="Remote"),
    )

    assert result is True
    fallback_container.stop.assert_called_once_with(timeout=10)
    fallback_container.remove.assert_called_once()
    cleanup_container.start.assert_called_once()


def test_availability_checker_host_component_health_handles_not_running_and_errors():
    host_operations = MagicMock()
    host_operations.get_docker_host_url.return_value = "tcp://10.0.0.5:2375"
    logger = MagicMock()
    docker_sdk_module = MagicMock()
    docker_sdk_module.errors.NotFound = type("NotFound", (Exception,), {})

    client = MagicMock()
    container = MagicMock()
    container.attrs = {"State": {"Running": False}}
    client.containers.get.return_value = container
    docker_sdk_module.DockerClient.return_value = client

    checker = ComposeAvailabilityChecker(
        docker_sdk_module=docker_sdk_module,
        host_operations=host_operations,
        logger=logger,
        http_client_cls=MagicMock(),
    )

    assert (
        checker._host_components_are_healthy(
            SimpleNamespace(name="Remote"),
            [SimpleNamespace(name="sensor")],
        )
        is False
    )
    client.close.assert_called_once()

    client = MagicMock()
    client.containers.get.side_effect = RuntimeError("boom")
    docker_sdk_module.DockerClient.return_value = client
    assert (
        checker._host_components_are_healthy(
            SimpleNamespace(name="Remote"),
            [SimpleNamespace(name="sensor")],
        )
        is False
    )
    logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_availability_checker_uses_host_fallback_and_sensor_urls():
    host_operations = MagicMock()
    host_operations.group_components_by_host.return_value = {
        1: [SimpleNamespace(name="sensor", host_system=None)]
    }

    requested_urls = []
    checker = ComposeAvailabilityChecker(
        docker_sdk_module=MagicMock(),
        host_operations=host_operations,
        logger=MagicMock(),
        http_client_cls=lambda timeout=3.0: FakeAsyncClient(
            {
                "http://sensor:8080/healthcheck": 200,
                "http://fallback:9000/healthcheck": 200,
            },
            requested_urls,
        ),
    )

    ids_system = SimpleNamespace(
        components=[
            SimpleNamespace(
                name="sensor",
                host_system=None,
                role="SENSOR",
                port=8080,
                get_http_url=lambda: "http://sensor:8080",
            ),
            SimpleNamespace(
                name="sensor-duplicate",
                host_system=None,
                role="SENSOR",
                port=8080,
                get_http_url=lambda: "http://sensor:8080",
            ),
        ],
        host_system=SimpleNamespace(name="FallbackHost"),
        get_container_http_url=lambda: "http://fallback:9000",
    )

    with patch(
        "app.deployment.deployment_plugins.docker_compose_support.availability.asyncio.to_thread",
        new_callable=AsyncMock,
    ) as mock_to_thread:
        mock_to_thread.return_value = True
        assert await checker._all_components_are_healthy(ids_system) is True

    assert await checker._all_sensor_endpoints_are_available(ids_system) is True
    assert requested_urls == ["http://sensor:8080/healthcheck"]

    ids_system.components = [
        SimpleNamespace(role="AGGREGATOR", port=8081, get_http_url=lambda: "unused")
    ]
    assert await checker._all_sensor_endpoints_are_available(ids_system) is True
    assert requested_urls[-1] == "http://fallback:9000/healthcheck"


@pytest.mark.asyncio
async def test_deployment_service_teardown_includes_hosts_without_components():
    host_with_components = SimpleNamespace(id=1, name="Main")
    extra_host = SimpleNamespace(id=2, name="Extra")
    component = SimpleNamespace(host_system=host_with_components, host_system_id=1)

    host_operations = MagicMock()
    host_operations.group_components_by_host.return_value = {1: [component]}
    host_operations.teardown_project = AsyncMock(return_value=True)

    spec_manager = MagicMock()
    spec_manager.build_paths.side_effect = lambda container_id, host_name: f"{container_id}:{host_name}"

    service = ComposeDeploymentService(
        get_host_by_id=AsyncMock(),
        spec_manager=spec_manager,
        host_operations=host_operations,
    )

    await service.teardown(
        SimpleNamespace(
            id=4,
            components=[component],
            _deployment_hosts=[extra_host],
        )
    )

    assert host_operations.teardown_project.await_count == 2
