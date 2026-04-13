import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import docker as docker_sdk
from app.deployment.deployment_plugins.docker import (
    DOCKER_DEPLOYMENT_CLIENT_TIMEOUT,
)
from app.models.docker_host_system import (
    DockerHostSystem,
    set_host_status,
    get_host_by_id,
    get_all_hosts,
    add_host_system,
    remove_host,
)
from app.utils import DOCKER_HOST_STATUS
from app.test.fixtures import *


# ==================== FIXTURES ====================


@pytest.fixture
def core_host():
    return DockerHostSystem(
        id=1, name="Core Host", host="localhost", docker_port=2375, status="available"
    )


@pytest.fixture
def remote_host():
    return DockerHostSystem(
        id=2,
        name="Remote Worker",
        host="192.168.1.100",
        docker_port=2376,
        status="available",
    )


# ==================== get_host_and_docker_port ====================


def test_get_host_and_docker_port_core_host(core_host: DockerHostSystem):
    """When host name contains 'Core', should return the core host IP."""
    with patch("app.models.docker_host_system.get_core_host_ip", return_value="172.17.0.1"):
        host, port = core_host.get_host_and_docker_port()
        assert host == "172.17.0.1"
        assert port == 2375


def test_get_host_and_docker_port_localhost(core_host: DockerHostSystem):
    """When host is 'localhost', should return core host IP even if name doesn't contain 'Core'."""
    core_host.name = "SomeOtherName"
    core_host.host = "localhost"
    with patch("app.models.docker_host_system.get_core_host_ip", return_value="172.17.0.1"):
        host, port = core_host.get_host_and_docker_port()
        assert host == "172.17.0.1"
        assert port == 2375


def test_get_host_and_docker_port_remote_host(remote_host: DockerHostSystem):
    """When host is remote, should return its own host/port."""
    host, port = remote_host.get_host_and_docker_port()
    assert host == "192.168.1.100"
    assert port == 2376


def test_get_metric_service_image_uses_name_and_version_env(
    remote_host: DockerHostSystem,
):
    with patch.dict(
        "os.environ",
        {
            "METRIC_SERVICE_IMAGE_NAME": "ghcr.io/example/custom-metric-service",
            "METRIC_SERVICE_IMAGE_VERSION": "v1.2.3",
        },
    ):
        assert (
            remote_host.get_metric_service_image()
            == "ghcr.io/example/custom-metric-service:v1.2.3"
        )


def test_get_metric_service_metric_endpoint_uses_core_pushgateway(
    remote_host: DockerHostSystem,
):
    with patch(
        "app.models.docker_host_system.get_external_prometheus_push_gateway_url",
        return_value="http://172.17.0.1:9091",
    ):
        assert (
            remote_host.get_metric_service_metric_endpoint()
            == "http://172.17.0.1:9091/metrics/job/metric_service_host_2"
        )


def test_get_metric_service_metric_endpoint_uses_localhost_for_core_host(
    core_host: DockerHostSystem,
):
    with patch.dict("os.environ", {"EXTERNAL_FASTAPI_PORT": "8000"}), patch(
        "app.models.docker_host_system.get_prometheus_push_gateway_url",
        return_value="http://prometheus-push-gateway:9091",
    ):
        assert (
            core_host.get_metric_service_metric_endpoint()
            == "http://127.0.0.1:9091/metrics/job/metric_service_host_1"
        )


def test_get_metric_service_registration_ip_uses_accessible_host_for_core_host(
    core_host: DockerHostSystem,
):
    with patch(
        "app.models.docker_host_system.get_core_host_ip",
        return_value="172.17.0.1",
    ), patch(
        "app.models.docker_host_system.socket.gethostbyname_ex",
        return_value=("172.17.0.1", [], ["172.17.0.1"]),
    ):
        assert core_host.get_metric_service_registration_ip() == "172.17.0.1"


def test_resolve_host_aliases_includes_registration_ip_for_core_host(
    core_host: DockerHostSystem,
):
    with patch(
        "app.models.docker_host_system.get_core_host_ip",
        return_value="172.17.0.1",
    ), patch(
        "app.models.docker_host_system.DockerHostSystem.get_metric_service_registration_ip",
        return_value="172.17.0.1",
    ), patch(
        "app.models.docker_host_system.socket.gethostbyname_ex",
        side_effect=[
            ("localhost", [], ["127.0.0.1"]),
            ("172.17.0.1", [], ["172.17.0.1"]),
        ],
    ):
        aliases = core_host.resolve_host_aliases()

    assert "172.17.0.1" in aliases
    assert "127.0.0.1" in aliases
    assert "localhost" in aliases


def test_get_metric_service_registration_endpoint_uses_host_specific_route(
    remote_host: DockerHostSystem,
):
    with patch("app.models.docker_host_system.get_core_url", return_value="http://core:8000"):
        assert (
            remote_host.get_metric_service_registration_endpoint()
            == "http://core:8000/metric-services/register/2"
        )


def test_get_metric_service_registration_endpoint_uses_localhost_for_core_host(
    core_host: DockerHostSystem,
):
    with patch.dict("os.environ", {"EXTERNAL_FASTAPI_PORT": "8000"}):
        assert (
            core_host.get_metric_service_registration_endpoint()
            == "http://127.0.0.1:8000/metric-services/register/1"
        )


@pytest.mark.asyncio
async def test_choose_metric_service_port_returns_first_available(
    remote_host: DockerHostSystem,
):
    remote_host.is_metric_service_port_available = AsyncMock(
        side_effect=[False, True]
    )

    with patch(
        "app.models.docker_host_system.random.randint",
        side_effect=[21001, 21002],
    ):
        port = await remote_host.choose_metric_service_port()

    assert port == 21002


@pytest.mark.asyncio
async def test_deploy_metric_service_uses_deployment_timeout(
    remote_host: DockerHostSystem,
):
    async def run_immediately(func, *args, **kwargs):
        return func(*args, **kwargs)

    metric_service = MagicMock()
    mock_client = MagicMock()
    mock_client.close = MagicMock()
    mock_container = MagicMock()
    mock_client.containers.create.return_value = mock_container
    remote_host.choose_metric_service_port = AsyncMock(return_value=21002)

    with patch(
        "app.models.docker_host_system.get_or_create_metric_service",
        new=AsyncMock(return_value=metric_service),
    ), patch(
        "app.models.docker_host_system.update_metric_service",
        new=AsyncMock(),
    ), patch(
        "app.models.docker_host_system.get_docker_client",
        return_value=mock_client,
    ) as mock_get_client, patch(
        "app.models.docker_host_system.ensure_image_present",
        new=AsyncMock(),
    ) as mock_ensure_image_present, patch(
        "app.models.docker_host_system.asyncio.to_thread",
        new=AsyncMock(side_effect=run_immediately),
    ):
        await remote_host._deploy_metric_service(AsyncMock())

    mock_get_client.assert_called_once_with(
        remote_host,
        timeout=DOCKER_DEPLOYMENT_CLIENT_TIMEOUT,
    )
    mock_ensure_image_present.assert_awaited_once_with(
        mock_client,
        remote_host.get_metric_service_image(),
    )
    mock_container.start.assert_called_once()
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_remove_metric_service_container_existing(
    remote_host: DockerHostSystem,
):
    async def run_immediately(func, *args, **kwargs):
        return func(*args, **kwargs)

    mock_container = MagicMock()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_client.close = MagicMock()

    with patch(
        "app.models.docker_host_system.get_docker_client", return_value=mock_client
    ), patch(
        "app.models.docker_host_system.asyncio.to_thread",
        new=AsyncMock(side_effect=run_immediately),
    ):
        await remote_host.remove_metric_service_container()

    mock_client.containers.get.assert_called_once_with(
        remote_host.get_metric_service_container_name()
    )
    mock_container.remove.assert_called_once_with(force=True)
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_remove_metric_service_container_missing(
    remote_host: DockerHostSystem,
):
    async def run_immediately(func, *args, **kwargs):
        return func(*args, **kwargs)

    mock_client = MagicMock()
    mock_client.containers.get.side_effect = docker_sdk.errors.NotFound("missing")
    mock_client.close = MagicMock()

    with patch(
        "app.models.docker_host_system.get_docker_client", return_value=mock_client
    ), patch(
        "app.models.docker_host_system.asyncio.to_thread",
        new=AsyncMock(side_effect=run_immediately),
    ):
        await remote_host.remove_metric_service_container()

    mock_client.containers.get.assert_called_once_with(
        remote_host.get_metric_service_container_name()
    )
    mock_client.close.assert_called_once()


# ==================== check_host_health ====================


@pytest.mark.asyncio
async def test_check_host_health_available(core_host: DockerHostSystem):
    """When host is reachable and Docker responds, should return AVAILABLE."""
    core_host.is_host_reachable = AsyncMock(return_value=True)
    core_host._check_metric_service_health = AsyncMock(return_value=True)
    mock_client = MagicMock()
    mock_client.version.return_value = {"Version": "20.10.17"}
    mock_client.close = MagicMock()

    with patch("app.models.docker_host_system.get_docker_client", return_value=mock_client):
        result = await core_host.check_host_health(AsyncMock())
        assert result == DOCKER_HOST_STATUS.AVAILABLE.value


@pytest.mark.asyncio
async def test_check_host_health_unreachable(core_host: DockerHostSystem):
    """When host is not reachable, should return UNAVAILABLE."""
    core_host.is_host_reachable = AsyncMock(return_value=False)

    result = await core_host.check_host_health()
    assert result == DOCKER_HOST_STATUS.UNAVAILABLE.value


@pytest.mark.asyncio
async def test_check_host_health_docker_no_version(core_host: DockerHostSystem):
    """When Docker client returns falsy version, should return UNAVAILABLE."""
    core_host.is_host_reachable = AsyncMock(return_value=True)
    mock_client = MagicMock()
    mock_client.version.return_value = None
    mock_client.close = MagicMock()
    core_host._mark_metric_service_unavailable = AsyncMock()

    with patch("app.models.docker_host_system.get_docker_client", return_value=mock_client):
        result = await core_host.check_host_health(AsyncMock())
        assert result == DOCKER_HOST_STATUS.UNAVAILABLE.value


@pytest.mark.asyncio
async def test_check_host_health_exception(core_host: DockerHostSystem):
    """When Docker client raises an exception, should return UNAVAILABLE."""
    core_host.is_host_reachable = AsyncMock(return_value=True)
    core_host._mark_metric_service_unavailable = AsyncMock()

    with patch(
        "app.models.docker_host_system.get_docker_client",
        side_effect=Exception("Connection refused"),
    ):
        result = await core_host.check_host_health(AsyncMock())
        assert result == DOCKER_HOST_STATUS.UNAVAILABLE.value


# ==================== is_host_reachable ====================


@pytest.mark.asyncio
async def test_is_host_reachable_success(remote_host: DockerHostSystem):
    """When TCP connection succeeds, should return True."""
    mock_writer = MagicMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()

    with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for:
        mock_wait_for.return_value = (MagicMock(), mock_writer)
        result = await remote_host.is_host_reachable()
        assert result is True
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_host_reachable_timeout(remote_host: DockerHostSystem):
    """When TCP connection times out, should return False."""
    import asyncio

    with patch("asyncio.open_connection", return_value=MagicMock()):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = await remote_host.is_host_reachable(timeout=0.1)
            assert result is False


@pytest.mark.asyncio
async def test_is_host_reachable_connection_refused(remote_host: DockerHostSystem):
    """When TCP connection is refused, should return False."""
    with patch("asyncio.open_connection", return_value=MagicMock()):
        with patch("asyncio.wait_for", side_effect=ConnectionRefusedError):
            result = await remote_host.is_host_reachable()
            assert result is False


# ==================== update_availability ====================


@pytest.mark.asyncio
async def test_update_availability_status_changed(core_host: DockerHostSystem):
    """When health status changes, should update via set_host_status."""
    core_host.status = DOCKER_HOST_STATUS.AVAILABLE.value
    core_host.check_host_health = AsyncMock(
        return_value=DOCKER_HOST_STATUS.UNAVAILABLE.value
    )
    mock_db = AsyncMock()

    with patch(
        "app.models.docker_host_system.set_host_status", new_callable=AsyncMock
    ) as mock_set:
        await core_host.update_availability(mock_db)
        mock_set.assert_awaited_once_with(
            mock_db, core_host, DOCKER_HOST_STATUS.UNAVAILABLE.value
        )


@pytest.mark.asyncio
async def test_update_availability_status_unchanged(core_host: DockerHostSystem):
    """When health status hasn't changed, should NOT call set_host_status."""
    core_host.status = DOCKER_HOST_STATUS.AVAILABLE.value
    core_host.check_host_health = AsyncMock(
        return_value=DOCKER_HOST_STATUS.AVAILABLE.value
    )
    mock_db = AsyncMock()

    with patch(
        "app.models.docker_host_system.set_host_status", new_callable=AsyncMock
    ) as mock_set:
        await core_host.update_availability(mock_db)
        mock_set.assert_not_awaited()


# ==================== QUERY FUNCTIONS ====================


@pytest.mark.asyncio
async def test_set_host_status(core_host: DockerHostSystem):
    """Should set status on host and commit/refresh."""
    mock_db = AsyncMock()
    await set_host_status(mock_db, core_host, DOCKER_HOST_STATUS.UNAVAILABLE.value)
    assert core_host.status == DOCKER_HOST_STATUS.UNAVAILABLE.value
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(core_host)


@pytest.mark.asyncio
async def test_get_host_by_id(db_session_fixture: DatabaseSessionFixture):
    """Should return a host when queried by ID."""
    db = await db_session_fixture.get_db_session()
    result = await get_host_by_id(db, 1)
    assert result is not None
    assert result.name == "localhost"


@pytest.mark.asyncio
async def test_get_all_hosts(db_session_fixture: DatabaseSessionFixture):
    """Should return all hosts."""
    db = await db_session_fixture.get_db_session()
    result = await get_all_hosts(db)
    assert isinstance(result, list)
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_add_host_system():
    """Should add host, check health, commit and refresh."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    host = DockerHostSystem(
        name="test",
        host="10.0.0.1",
        docker_port=2375,
        status=DOCKER_HOST_STATUS.UNAVAILABLE.value,
    )
    host.check_host_health = AsyncMock(return_value=DOCKER_HOST_STATUS.AVAILABLE.value)

    await add_host_system(mock_db, host)
    mock_db.add.assert_called_once_with(host)
    host.check_host_health.assert_awaited_once()
    assert host.status == DOCKER_HOST_STATUS.AVAILABLE.value
    assert mock_db.commit.await_count == 2
    assert mock_db.refresh.await_count == 2


@pytest.mark.asyncio
async def test_remove_host_existing(remote_host: DockerHostSystem):
    """Should delete an existing host."""
    mock_db = AsyncMock()
    with patch(
        "app.models.docker_host_system.get_host_by_id",
        new=AsyncMock(return_value=remote_host),
    ), patch.object(
        remote_host, "remove_metric_service_container", new=AsyncMock()
    ) as mock_remove_metric_service_container:
        removed = await remove_host(mock_db, remote_host.id)

    assert removed is True
    mock_remove_metric_service_container.assert_awaited_once()
    mock_db.delete.assert_awaited_once_with(remote_host)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_host_nonexistent():
    """Should not call delete when host doesn't exist."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    removed = await remove_host(mock_db, 999)

    assert removed is False
    mock_db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_host_raises_when_metric_service_cleanup_fails(
    remote_host: DockerHostSystem,
):
    mock_db = AsyncMock()

    with patch(
        "app.models.docker_host_system.get_host_by_id",
        new=AsyncMock(return_value=remote_host),
    ), patch.object(
        remote_host,
        "remove_metric_service_container",
        new=AsyncMock(side_effect=RuntimeError("docker unavailable")),
    ):
        with pytest.raises(RuntimeError, match="Could not remove metric service"):
            await remove_host(mock_db, remote_host.id)

    mock_db.delete.assert_not_awaited()
