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
from app.test.fixtures import *

@pytest.mark.asyncio
async def test_setup_ids(db_session_fixture: DatabaseSessionFixture, mock_stream_metric_tasks):
    request_data: IdsContainerCreate = IdsContainerCreate(   
        host_system_id=1,
        description= "Test IDS Container",
        configuration_id= 1,
        ids_tool_id= 1,
    )

    db_session = db_session_fixture.get_db_session()
    response = await setup_ids(request_data, db=db_session, stream_metric_tasks=mock_stream_metric_tasks)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 200
    assert response_json == {"message": "setup done"}


@pytest.mark.asyncio
async def test_remove_container(db_session_fixture: DatabaseSessionFixture, mock_stream_metric_tasks):
    db_session = db_session_fixture.get_db_session()
    container_id = 1
    response = await remove_container(container_id=container_id,db=db_session, stream_metric_tasks=mock_stream_metric_tasks)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 204
    assert response_json == {"message": "teardown done"}

@pytest.mark.asyncio
async def test_start_static_container_analysis_from_idle_container(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 200
    mock_ids_container.start_static_analysis.return_value = mock_response

    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response_json)
    assert response.status_code == 200
    assert response_json == { "message": "container 1 - static analysis triggered" }


@pytest.mark.asyncio
async def test_start_static_container_analysis_from_idle_container_unsuccesfully(
    db_session_fixture: DatabaseSessionFixture
    ):
    db_session = db_session_fixture.get_db_session()
    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )
    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 500 
    mock_ids_container.start_static_analysis.return_value = mock_response

    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"error": "container 1 - static analysis could not be triggered"}



@pytest.mark.asyncio
async def test_start_static_container_analysis_from_busy_container(
    db_session_fixture: DatabaseSessionFixture
    ):
    db_session = db_session_fixture.get_db_session()
    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )
    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.status = STATUS.ACTIVE.value
    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not Idle!, aborting"}

@pytest.mark.asyncio
async def test_start_static_container_analysis_from_unavailable_container(
    db_session_fixture: DatabaseSessionFixture
    ):
    db_session = db_session_fixture.get_db_session()
    static_analysis_mock_data: StaticAnalysisData = StaticAnalysisData(
        container_id = 1,
        ensemble_id = None,
        dataset_id=1
    )
    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.is_available = AsyncMock(return_value = False)

    response = await start_static_container_analysis(static_analysis_data=static_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not available! Check if it should be deleted"}



#######
# Network Analyses
#######

@pytest.mark.asyncio
async def test_start_network_container_analysis_from_idle_container(
    db_session_fixture: DatabaseSessionFixture
    ):
    db_session = db_session_fixture.get_db_session()
    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.return_value.status_code = 200 

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.start_network_analysis = mock_response

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == { "message": "container 1 - network analysis triggered" }



@pytest.mark.asyncio
async def test_start_network_container_analysis_from_idle_container_unsuccesfully(
    db_session_fixture: DatabaseSessionFixture
    ):
    db_session = db_session_fixture.get_db_session()
    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.return_value.status_code = 500 

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.start_network_analysis = mock_response

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"error": "container 1 - network analysis could not be triggered"}



@pytest.mark.asyncio
async def test_start_network_container_analysis_from_busy_container(
    db_session_fixture: DatabaseSessionFixture
    ):
    db_session = db_session_fixture.get_db_session()
    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.status = STATUS.ACTIVE.value

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not Idle!, aborting"}

@pytest.mark.asyncio
async def test_start_network_container_analysis_from_unavailable_container(
    db_session_fixture: DatabaseSessionFixture
    ):
    db_session = db_session_fixture.get_db_session()
    network_analysis_mock_data: NetworkAnalysisData = NetworkAnalysisData(
        container_id = 1,
        ensemble_id = None,
    )
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.return_value.status_code = 200 

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.start_network_analysis = mock_response
    mock_ids_container.is_available = AsyncMock(return_value = False)

    response = await start_network_container_analysis(network_analysis_data=network_analysis_mock_data,db=db_session)
    response_json = json.loads(response.body.decode())

    assert response.status_code == 500
    assert response_json == {"content": "container with id 1 is not available! Check if it should be deleted"}


@pytest.mark.asyncio
async def test_stop_analysis_successfully(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    stop_analysis_data: stop_analysisData = stop_analysisData(
        container_id = 1,
    )
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.return_value.status_code = 200

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.stop_analysis = mock_response

    response = await stop_analysis(stop_data=stop_analysis_data, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == { "message": f"Analysis for container {stop_analysis_data.container_id} stopped successfully" }

@pytest.mark.asyncio
async def test_stop_analysis_unsuccessfully(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    stop_analysis_data: stop_analysisData = stop_analysisData(
        container_id = 1,
    )
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.return_value.status_code = 500

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.stop_analysis = mock_response

    response = await stop_analysis(stop_data=stop_analysis_data, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 500
    assert response_json == { "error": f"Analysis for container {stop_analysis_data.container_id} did not stop successfully" }



@pytest.mark.asyncio
async def test_finished_analysis(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    analysis_finished_data: AnalysisFinishedData = AnalysisFinishedData(
        container_id = 1
    )

    mock_ids_container = db_session_fixture.get_ids_container_model()

    response = await finished_analysis(analysisFinishedData=analysis_finished_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == { "message": f"Successfully stopped analysis for container {mock_ids_container.name}" }



@patch("app.routers.ids.push_alerts_to_loki")
@pytest.mark.asyncio
async def test_receive_alerts_from_ids_network(push_alerts_mock, db_session_fixture: DatabaseSessionFixture, mock_background_tasks):
    db_session = db_session_fixture.get_db_session()
    alert_data: AlertData = AlertData(
        analysis_type = "network",
        dataset_id = 1,
        container_id = 1,
        alerts = [
            {
                "time": "2025-01-01T12:00:00Z",
                "destination_ip": "192.168.0.1",
                "destination_port": "8080",
                "source_ip": "10.0.0.1",
                "source_port": "1234",
                "severity": 0,
                "type": "test alert",
                "message": "Test alert message",
            }
        ]
    )

    response = await receive_alerts_from_ids(alert_data=alert_data,db=db_session, background_tasks=mock_background_tasks)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': 'Successfully pushed alerts and metrics to Loki'}




@patch("app.routers.ids.push_alerts_to_loki")
@patch("app.routers.ids.calculate_evaluation_metrics_and_push")
@pytest.mark.asyncio
async def test_receive_alerts_from_ids_static(calculate_and_push_mock, push_alerts_mock, db_session_fixture: DatabaseSessionFixture, mock_background_tasks):
    db_session = db_session_fixture.get_db_session()
    alert_data: AlertData = AlertData(
        analysis_type = "static",
        dataset_id = 1,
        container_id = 1,
        alerts = [
            {
                "time": "2025-01-01T12:00:00Z",
                "destination_ip": "192.168.0.1",
                "destination_port": "8080",
                "source_ip": "10.0.0.1",
                "source_port": "1234",
                "severity": 0,
                "type": "test alert",
                "message": "Test alert message",
            }
        ]
    )
    response = await receive_alerts_from_ids(alert_data=alert_data,db=db_session, background_tasks=mock_background_tasks)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': 'Successfully pushed alerts and metrics to Loki'}