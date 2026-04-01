import pytest
from unittest.mock import patch, MagicMock, AsyncMock
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


# ==================== check_host_health ====================


@pytest.mark.asyncio
async def test_check_host_health_available(core_host: DockerHostSystem):
    """When host is reachable and Docker responds, should return AVAILABLE."""
    core_host.is_host_reachable = AsyncMock(return_value=True)
    mock_client = MagicMock()
    mock_client.version.return_value = {"Version": "20.10.17"}

    with patch("app.models.docker_host_system.get_docker_client", return_value=mock_client):
        result = await core_host.check_host_health()
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

    with patch("app.models.docker_host_system.get_docker_client", return_value=mock_client):
        result = await core_host.check_host_health()
        assert result == DOCKER_HOST_STATUS.UNAVAILABLE.value


@pytest.mark.asyncio
async def test_check_host_health_exception(core_host: DockerHostSystem):
    """When Docker client raises an exception, should return UNAVAILABLE."""
    core_host.is_host_reachable = AsyncMock(return_value=True)

    with patch(
        "app.models.docker_host_system.get_docker_client",
        side_effect=Exception("Connection refused"),
    ):
        result = await core_host.check_host_health()
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

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await remote_host.is_host_reachable(timeout=0.1)
        assert result is False


@pytest.mark.asyncio
async def test_is_host_reachable_connection_refused(remote_host: DockerHostSystem):
    """When TCP connection is refused, should return False."""
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
    host = DockerHostSystem(name="test", host="10.0.0.1", docker_port=2375)
    host.check_host_health = AsyncMock(return_value=DOCKER_HOST_STATUS.AVAILABLE.value)

    await add_host_system(mock_db, host)
    mock_db.add.assert_called_once_with(host)
    host.check_host_health.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(host)


@pytest.mark.asyncio
async def test_remove_host_existing(db_session_fixture: DatabaseSessionFixture):
    """Should delete an existing host."""
    db = await db_session_fixture.get_db_session()
    await remove_host(db, 1)
    db.delete.assert_awaited_once()
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_remove_host_nonexistent():
    """Should not call delete when host doesn't exist."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    await remove_host(mock_db, 999)
    mock_db.delete.assert_not_awaited()
