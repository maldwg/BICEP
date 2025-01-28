import pytest
from docker import DockerClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.test.fixtures import *
from app.models.ids_container import *
from app.utils import STATUS, get_core_host

@pytest.fixture
def mock_ids_container():
    mock_host_system = DockerHostSystem(
        id = 1,
        name = "localhost",
        host = "localhost",
        docker_port = 2375
    )
    ids_container = IdsContainer(
        id = 1,
        name = "Test IDS",
        port = 8080,
        status = STATUS.IDLE.value,
        description = "Test Description",
        stream_metric_task_id = None,
        configuration_id = 1,
        ids_tool_id = 1,
        ruleset_id = 1,
        host_system_id = 1,
        host_system = mock_host_system
    )
    return ids_container
@patch("app.models.ids_container.start_metric_stream")
@pytest.mark.asyncio
async def test_start_metric_collection(start_metric_stream_mock,mock_ids_container: IdsContainer, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_stream_metric_tasks = {}
    response = await mock_ids_container.start_metric_collection(db=db_session,stream_metric_tasks=mock_stream_metric_tasks)
    assert response == f"started metric collection for container {mock_ids_container.id}"

@patch("app.models.ids_container.stop_metric_stream")
@pytest.mark.asyncio
async def test_stop_metric_collection_without_task_id(stop_metric_stream_mock, mock_ids_container: IdsContainer, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_stream_metric_tasks = {}
    response = await mock_ids_container.stop_metric_collection(db=db_session, stream_metric_tasks=mock_stream_metric_tasks)
    assert response == f"Could not stop metric collection for container {mock_ids_container.id}; No stream started"

@patch("app.models.ids_container.stop_metric_stream")
@pytest.mark.asyncio
async def test_stop_metric_collection_without_task_id_in_stream_set(stop_metric_stream_mock, mock_ids_container: IdsContainer, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_ids_container.stream_metric_task_id = 12345
    mock_stream_metric_tasks = {}
    response = await mock_ids_container.stop_metric_collection(db=db_session, stream_metric_tasks=mock_stream_metric_tasks)
    assert response == f"Could not stop task id {mock_ids_container.stream_metric_task_id} in container {mock_ids_container.id}, skipping cancellation of the task"

@patch("app.models.ids_container.stop_metric_stream")
@pytest.mark.asyncio
async def test_stop_metric_collection(stop_metric_stream_mock, mock_ids_container: IdsContainer, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_ids_container.stream_metric_task_id = 12345
    mock_stream_metric_tasks = {}
    mock_stream_metric_tasks[mock_ids_container.stream_metric_task_id] = "task-process-mock"
    response = await mock_ids_container.stop_metric_collection(db=db_session, stream_metric_tasks=mock_stream_metric_tasks)
    assert response == f"stopped metric collection for container {mock_ids_container.id}"

@pytest.mark.asyncio
async def test_is_busy(mock_ids_container: IdsContainer):
    mock_ids_container.status = STATUS.ACTIVE.value
    assert await mock_ids_container.is_busy() is True

@pytest.mark.asyncio
async def test_is_not_busy(mock_ids_container: IdsContainer):
    mock_ids_container.status = STATUS.IDLE.value
    assert await mock_ids_container.is_busy() is False


def test_get_container_http_url_localhost(mock_ids_container: IdsContainer):
    docker_host = mock_ids_container.get_container_http_url()
    core_host = get_core_host()
    docker_host = mock_ids_container.get_container_http_url()
    assert docker_host == f"http://{core_host}:{mock_ids_container.port}"

def test_get_container_http_url_core(mock_ids_container: IdsContainer):
    mock_ids_container.host_system.name = "Core"
    core_host = get_core_host()
    docker_host = mock_ids_container.get_container_http_url()
    assert docker_host == f"http://{core_host}:{mock_ids_container.port}"

def test_get_container_http_url_proper_host(mock_ids_container: IdsContainer):
    mock_ids_container.host_system.name = "proper_host"
    mock_ids_container.host_system.host = "my-custom-dns-name"
    docker_host = mock_ids_container.get_container_http_url()
    assert docker_host == f"http://{mock_ids_container.host_system.host}:{mock_ids_container.port}"