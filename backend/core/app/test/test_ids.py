import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app 
from app.database import get_db
from app.utils import get_stream_metric_tasks
from app.routers.ids import *
from app.validation.models import *
from app.models.docker_host_system import DockerHostSystem
from http.client import HTTPResponse

@pytest.fixture
def db_session():
    mock_db = MagicMock()
    yield mock_db

@pytest.fixture
def mock_stream_metric_tasks():
    return AsyncMock()

@pytest.fixture
def mock_background_tasks():
    """
    Mock the BackgroundTasks instance.
    """
    tasks = MagicMock(spec=set())
    tasks.add_task = MagicMock()
    return tasks

@patch("app.models.ids_container.IdsContainer.setup")
@patch("app.models.docker_host_system.get_host_by_id")
@patch("app.models.ids_container.IdsContainer.start_metric_collection")
@pytest.mark.asyncio
async def test_setup_ids(_, docker_host_mock,__ ,db_session, mock_stream_metric_tasks):
    docker_host_mock.return_value = DockerHostSystem(
        id = 0,
        name = "localhost",
        host = "localhost",
        docker_port = 2375
    )
    request_data: IdsContainerCreate = IdsContainerCreate(   
        host_system_id=1,
        description= "Test IDS Container",
        configuration_id= 1,
        ids_tool_id= 1,
    )
    response = await setup_ids(request_data, db=db_session, stream_metric_tasks=mock_stream_metric_tasks)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 200
    assert response_json == {"message": "setup done"}


@patch("app.models.ids_container.IdsContainer.stop_metric_collection")
@patch("app.models.ids_container.IdsContainer.teardown")
@patch("app.models.ids_container.IdsContainer.stop_analysis")
@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_remove_container(get_container_mock,_,__,___, db_session, mock_stream_metric_tasks):
    db_session = AsyncMock()
    container_id = 1
    get_container_mock.return_value = AsyncMock(spec=IdsContainer)
    response = await remove_container(container_id=container_id,db=db_session, stream_metric_tasks=mock_stream_metric_tasks)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 204
    assert response_json == {"message": "teardown done"}

@patch("app.routers.ids.update_container_status")
@patch("app.routers.ids.get_dataset_by_id")
@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_static_container_analysis_from_idle_container(
    get_container_mock, 
    get_dataset_mock, 
    update_container_status_mock, 
    db_session
    ):

    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )
    start_static_analysis_mock = AsyncMock(spec=HTTPResponse)
    start_static_analysis_mock.return_value.status_code = 200 

    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.IDLE.value
    get_container_mock.return_value.id = 1
    get_container_mock.return_value.start_static_analysis = start_static_analysis_mock

    get_dataset_mock.return_value = MagicMock(spec=Dataset)
    get_dataset_mock.return_value.id = 1

    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == { "message": "container 1 - static analysis triggered" }


@patch("app.routers.ids.update_container_status")
@patch("app.routers.ids.get_dataset_by_id")
@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_static_container_analysis_from_idle_container_unsuccesfully(
    get_container_mock, 
    get_dataset_mock, 
    update_container_status_mock, 
    db_session
    ):

    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )
    start_static_analysis_mock = AsyncMock(spec=HTTPResponse)
    start_static_analysis_mock.return_value.status_code = 500 

    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.IDLE.value
    get_container_mock.return_value.id = 1
    get_container_mock.return_value.start_static_analysis = start_static_analysis_mock

    get_dataset_mock.return_value = MagicMock(spec=Dataset)
    get_dataset_mock.return_value.id = 1

    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"error": "container 1 - static analysis could not be triggered"}



@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_static_container_analysis_from_busy_container(
    get_container_mock, 
    db_session
    ):

    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )
    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.ACTIVE.value
    get_container_mock.return_value.id = 1
    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not Idle!, aborting"}

@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_static_container_analysis_from_unavailable_container(
    get_container_mock, 
    db_session
    ):

    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )
    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.IDLE.value
    get_container_mock.return_value.id = 1
    get_container_mock.return_value.is_available = AsyncMock(return_value = False)

    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not available! Check if it should be deleted"}



#######
# Network Analyses
#######

@patch("app.routers.ids.update_container_status")
@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_network_container_analysis_from_idle_container(
    get_container_mock, 
    update_container_status_mock, 
    db_session
    ):

    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    start_network_analysis_mock = AsyncMock(spec=HTTPResponse)
    start_network_analysis_mock.return_value.status_code = 200 

    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.IDLE.value
    get_container_mock.return_value.id = 1
    get_container_mock.return_value.start_network_analysis = start_network_analysis_mock

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == { "message": "container 1 - network analysis triggered" }





@patch("app.routers.ids.update_container_status")
@patch("app.routers.ids.get_dataset_by_id")
@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_network_container_analysis_from_idle_container_unsuccesfully(
    get_container_mock, 
    get_dataset_mock, 
    update_container_status_mock, 
    db_session
    ):

    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    start_network_analysis_mock = AsyncMock(spec=HTTPResponse)
    start_network_analysis_mock.return_value.status_code = 500 

    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.IDLE.value
    get_container_mock.return_value.id = 1
    get_container_mock.return_value.start_network_analysis = start_network_analysis_mock

    get_dataset_mock.return_value = MagicMock(spec=Dataset)
    get_dataset_mock.return_value.id = 1

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"error": "container 1 - network analysis could not be triggered"}



@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_network_container_analysis_from_busy_container(
    get_container_mock, 
    db_session
    ):

    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.ACTIVE.value
    get_container_mock.return_value.id = 1

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not Idle!, aborting"}

@patch("app.routers.ids.get_container_by_id")
@pytest.mark.asyncio
async def test_start_network_container_analysis_from_unavailable_container(
    get_container_mock, 
    db_session
    ):
    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    start_network_analysis_mock = AsyncMock(spec=HTTPResponse)
    start_network_analysis_mock.return_value.status_code = 200 

    get_container_mock.return_value = MagicMock(spec=IdsContainer)
    get_container_mock.return_value.status = STATUS.IDLE.value
    get_container_mock.return_value.id = 1
    get_container_mock.return_value.start_network_analysis = start_network_analysis_mock
    get_container_mock.return_value.is_available = AsyncMock(return_value = False)

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not available! Check if it should be deleted"}




# def test_stop_analysis(client):
#     request_data = {
#         "container_id": 1,
#     }

#     response = client.post("/ids/analysis/stop", json=request_data)

#     assert response.status_code in [200, 500]

# # Test for /ids/analysis/finished
# def test_finished_analysis(client):
#     request_data = {
#         "container_id": 1,
#     }

#     response = client.post("/ids/analysis/finished", json=request_data)

#     assert response.status_code == 200

# def test_receive_alerts_from_ids(client):
#     request_data = {
#         "container_id": 1,
#         "alerts": [
#             {
#                 "time": "2025-01-01T12:00:00Z",
#                 "destination_ip": "192.168.0.1",
#                 "destination_port": 8080,
#                 "source_ip": "10.0.0.1",
#                 "source_port": 1234,
#                 "severity": "high",
#                 "type": "test alert",
#                 "message": "Test alert message",
#             }
#         ],
#         "analysis_type": "static",
#         "dataset_id": 1,
#     }

#     response = client.post("/ids/publish/alerts", json=request_data)

#     assert response.status_code == 200
#     assert response.text == "Successfully pushed alerts and metrics to Loki"

# def test_display_background_tasks(client):
#     response = client.get("/ids/help/background-tasks")

#     assert response.status_code == 200