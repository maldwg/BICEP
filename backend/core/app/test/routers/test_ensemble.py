import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.validation.models import EnsembleCreate, StaticAnalysisData, NetworkAnalysisData, stop_analysisData, AnalysisFinishedData, AlertData
from app.routers.ensemble import *
from app.test.fixtures import *
from fastapi.responses import JSONResponse

@patch("app.models.ensemble.Ensemble.add_container")
@pytest.mark.asyncio
async def test_setup_ensembles_successfull(add_container_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    ensemble_data: EnsembleCreate = EnsembleCreate(
        name = "ensemble1",
        description="ensemble-test",
        technique= 0,
        container_ids= [0,1]
    )
    response = await setup_ensembles(ensembleData=ensemble_data,db=db_session)
    response_json = json.loads(response.body.decode())
    # Ensemble is None because the db transaction is only mocked there is no ID assignment to the Ensemble
    expected_content = [
        {'content': 'successfully added container 0 to ensemble None', 'status_code': 200}, 
        {'content': 'successfully added container 1 to ensemble None', 'status_code': 200}
    ]
    assert response.status_code == 200
    assert expected_content == response_json["content"]


@patch("app.routers.ensemble.deregister_container_from_ensemble", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_remove_ensemble_succesful(deregister_mock,db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    ensemble_id = 1

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 200
    deregister_mock.return_value = mock_response

    response = await remove_ensemble(ensemble_id=ensemble_id,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response.body)
    assert response.status_code == 200
    assert response_json == {"content":[{"content":"message successfully removed container 1 from ensemble 1","status_code":200}]}

@patch("app.routers.ensemble.deregister_container_from_ensemble", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_remove_ensemble_failiure(deregister_mock,db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    ensemble_id = 1

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 500
    deregister_mock.return_value = mock_response

    response = await remove_ensemble(ensemble_id=ensemble_id,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response.body)
    assert response.status_code == 200
    assert response_json == {"content":[{"content":" Did not remove container 1 from ensemble 1 successfully","status_code":500}]}


@pytest.mark.asyncio
async def test_start_static_ensemble_analysis_successful(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    static_analysis_data: StaticAnalysisData = StaticAnalysisData(
        ensemble_id = 1,
        dataset_id = 1
    )

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids_container])

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 200
    # needs to be bytes, otherwise deocde error in the tested function as decode method would be missing
    mock_response.body = b'{"message": "success"}'
    mock_ensemble.start_static_analysis.return_value = [mock_response]

    response = await start_static_ensemble_analysis(static_analysis_data=static_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response_json)
    assert response.status_code == 200
    assert response_json == {'content': [{'content': '{"message": "success"}', 'status_code': 200}]}


@pytest.mark.asyncio
async def test_start_static_ensemble_analysis_failiure(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    static_analysis_data: StaticAnalysisData = StaticAnalysisData(
        ensemble_id = 1,
        dataset_id = 1
    )

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids_container])

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 500
    # needs to be bytes, otherwise deocde error in the tested function as decode method would be missing
    mock_response.body = b'{"message": "failed"}'
    mock_ensemble.start_static_analysis.return_value = [mock_response]

    response = await start_static_ensemble_analysis(static_analysis_data=static_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response_json)
    assert response.status_code == 200
    # status code 500 is for the individual container, the 200 above for the overall call to the endpoint
    assert response_json == {'content': [{'content': '{"message": "failed"}', 'status_code': 500}]}


@pytest.mark.asyncio
async def test_start_static_ensemble_analysis_not_idle(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    static_analysis_data: StaticAnalysisData = StaticAnalysisData(
        ensemble_id = 1,
        dataset_id = 1
    )

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.status = STATUS.ACTIVE.value
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids_container])

    response = await start_static_ensemble_analysis(static_analysis_data=static_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 500
    assert response_json == {"error": f"container with id {mock_ids_container.id} is not Idle!, aborting"}


@pytest.mark.asyncio
async def test_start_static_ensemble_analysis_not_available(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    static_analysis_data: StaticAnalysisData = StaticAnalysisData(
        ensemble_id = 1,
        dataset_id = 1
    )

    mock_ids_container = db_session_fixture.get_ids_container_model()
    mock_ids_container.is_available = AsyncMock(return_value = False)
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids_container])

    response = await start_static_ensemble_analysis(static_analysis_data=static_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 500
    assert response_json == {"error": f"container with id {mock_ids_container.id} is not available! Check if it should be deleted"}


@pytest.mark.asyncio
async def test_stop_analysis(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()

    stop_data: stop_analysisData =  stop_analysisData(
        ensemble_id = 1
    )

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 200
    mock_ids = db_session_fixture.get_ids_container_model()
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids])
    mock_ids.stop_analysis.return_value = mock_response

    response = await stop_ensemble_analysis(stop_data, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': [{'content': f'Successfully stopped analysis for container {mock_ids.id} and ensemble {mock_ensemble.id}', 'status_code': 200}]}


@pytest.mark.asyncio
async def test_stop_analysis_unsuccessful(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()

    stop_data: stop_analysisData =  stop_analysisData(
        ensemble_id = 1
    )

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 500
    mock_ids = db_session_fixture.get_ids_container_model()
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids])
    mock_ids.stop_analysis.return_value = mock_response

    response = await stop_ensemble_analysis(stop_data, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': [{'content': f'Could not stop analysis for container {mock_ids.id} and ensemble {mock_ensemble.id}', 'status_code': 500}]}



@pytest.mark.asyncio
async def test_start_network_ensemble_analysis_successful(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    network_analysis_data: NetworkAnalysisData = NetworkAnalysisData(
        ensemble_id = 1
    )

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 200
    mock_response.body = b'{"message": "success"}'
    mock_ids = db_session_fixture.get_ids_container_model()
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids])
    mock_ensemble.start_network_analysis.return_value = [mock_response]
    
    response = await start_network_ensemble_analysis(network_analysis_data=network_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': [{'content': '{"message": "success"}', 'status_code': 200}]}


@pytest.mark.asyncio
async def test_start_network_ensemble_analysis_failiure(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    network_analysis_data: NetworkAnalysisData = NetworkAnalysisData(
        ensemble_id = 1
    )

    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 500
    mock_response.body = b'{"message": "failiure"}'
    mock_ids = db_session_fixture.get_ids_container_model()
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids])
    mock_ensemble.start_network_analysis.return_value = [mock_response]
    
    response = await start_network_ensemble_analysis(network_analysis_data=network_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': [{'content': '{"message": "failiure"}', 'status_code': 500}]}



@pytest.mark.asyncio
async def test_start_network_ensemble_analysis_unavailable(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    network_analysis_data: NetworkAnalysisData = NetworkAnalysisData(
        ensemble_id = 1
    )

    mock_ids = db_session_fixture.get_ids_container_model()
    mock_ids.is_available = AsyncMock(return_value = False)
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids])
    
    response = await start_network_ensemble_analysis(network_analysis_data=network_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 500
    assert response_json == {'error': 'container with id 1 is not available! Check if it should be deleted'}



@pytest.mark.asyncio
async def test_start_network_ensemble_analysis_not_idle(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    network_analysis_data: NetworkAnalysisData = NetworkAnalysisData(
        ensemble_id = 1
    )

    mock_ids = db_session_fixture.get_ids_container_model()
    mock_ids.status = STATUS.ACTIVE.value
    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.get_containers = MagicMock(return_value=[mock_ids])
    
    response = await start_network_ensemble_analysis(network_analysis_data=network_analysis_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 500
    assert response_json == {'error': 'container with id 1 is not Idle!, aborting'}

@pytest.mark.asyncio
async def test_finished_ensemble_analysis(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    finished_data: AnalysisFinishedData = AnalysisFinishedData(
        container_id = 1,
        ensemble_id = 1
    )

    response = await finished_ensemble_analysis(analysisFinishedData=finished_data,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response_json)
    assert response.status_code == 200
    assert response_json == { "message": f"Successfully finished analysis for esemble {finished_data.ensemble_id} and container {finished_data.container_id}" }



@patch("app.routers.ensemble.push_alerts_to_loki")
@pytest.mark.asyncio
async def test_receive_alerts_from_ids_unsuccessful_loki_push(push_to_loki_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    alert_data: AlertData = AlertData(
        analysis_type = "network",
        dataset_id = None,
        container_id = 1,
        ensemble_id = 1,
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
    mock_response_loki = AsyncMock(spec=HTTPResponse)
    mock_response_loki.status_code = 500
    push_to_loki_mock.return_value = mock_response_loki

    response = await receive_alerts_from_ids_for_ensemble(alert_data=alert_data,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response_json)
    assert response.status_code == 500
    assert response_json == {'content': 'Could not push logs to loki for container'}



@patch("app.routers.ensemble.get_alerts_from_analysis_id")
@patch("app.routers.ensemble.push_alerts_to_loki")
@pytest.mark.asyncio
async def test_receive_alerts_from_ids_network_analysis_last_container(push_to_loki_mock, get_alerts_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    alert_data: AlertData = AlertData(
        analysis_type = "network",
        dataset_id = None,
        container_id = 1,
        ensemble_id = 1,
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
    mock_response_loki = AsyncMock(spec=HTTPResponse)
    mock_response_loki.status_code = 204
    push_to_loki_mock.return_value = mock_response_loki

    # return value is not realy correct, but does not matter as the technique method is mocked as well inm its return value
    mock_response_get_alerts = AsyncMock(spec=[Alert],return_value=alert_data.alerts)
    get_alerts_mock.return_value = mock_response_get_alerts

    mock_technique = db_session_fixture.get_ensemble_technique_model()
    mock_technique.execute_technique_by_name_on_alerts.return_value = alert_data.alerts

    mock_ensemble = db_session_fixture.get_ensemble_model()

    response = await receive_alerts_from_ids_for_ensemble(alert_data=alert_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': f'Successfully pushed alerts for ensemble {mock_ensemble.name}'}


@patch("app.routers.ensemble.last_container_sending_logs", new_callable=AsyncMock)
@patch("app.routers.ensemble.push_alerts_to_loki")
@pytest.mark.asyncio
async def test_receive_alerts_from_ids_network_analysis_not_last_container(push_to_loki_mock, last_container_sending_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    alert_data: AlertData = AlertData(
        analysis_type = "network",
        dataset_id = None,
        container_id = 1,
        ensemble_id = 1,
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
    mock_response_loki = AsyncMock(spec=HTTPResponse)
    mock_response_loki.status_code = 204
    push_to_loki_mock.return_value = mock_response_loki
    last_container_sending_mock.return_value = False
    mock_container = db_session_fixture.get_ids_container_model()
    response = await receive_alerts_from_ids_for_ensemble(alert_data=alert_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': f'Successfully pushed alerts for container {mock_container.name}'}




@patch("app.routers.ensemble.last_container_sending_logs", new_callable=AsyncMock)
@patch("app.routers.ensemble.push_alerts_to_loki")
@pytest.mark.asyncio
async def test_receive_alerts_from_ids_static_analysis_not_last_container(push_to_loki_mock, last_container_sending_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    alert_data: AlertData = AlertData(
        analysis_type = "static",
        dataset_id = 1,
        container_id = 1,
        ensemble_id = 1,
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
    mock_response_loki = AsyncMock(spec=HTTPResponse)
    mock_response_loki.status_code = 204
    push_to_loki_mock.return_value = mock_response_loki
    last_container_sending_mock.return_value = False
    mock_container = db_session_fixture.get_ids_container_model()
    response = await receive_alerts_from_ids_for_ensemble(alert_data=alert_data,db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'content': f'Successfully pushed alerts for container {mock_container.name}'}

@patch("app.routers.ensemble.push_evaluation_metrics_to_prometheus")
@patch("app.routers.ensemble.calculate_evaluation_metrics")
@patch("app.routers.ensemble.clean_up_alerts_in_loki")
@patch("app.routers.ensemble.get_alerts_from_analysis_id")
@patch("app.routers.ensemble.push_alerts_to_loki")
@pytest.mark.asyncio
async def test_receive_alerts_from_ids_static_analysis_last_container(push_to_loki_mock, get_alerts_mock, cleanup_mock, calculate_metrics_mock, push_metrics_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    alert_data: AlertData = AlertData(
        analysis_type = "static",
        dataset_id = 1,
        container_id = 1,
        ensemble_id = 1,
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
    mock_response_loki = AsyncMock(spec=HTTPResponse)
    mock_response_loki.status_code = 204
    push_to_loki_mock.return_value = mock_response_loki


    # return value is not realy correct, but does not matter as the technique method is mocked as well inm its return value
    mock_response_get_alerts = AsyncMock(spec=[Alert],return_value=alert_data.alerts)
    get_alerts_mock.return_value = mock_response_get_alerts

    mock_technique = db_session_fixture.get_ensemble_technique_model()
    mock_technique.execute_technique_by_name_on_alerts.return_value = alert_data.alerts

    mock_ensemble = db_session_fixture.get_ensemble_model()

    mock_container = db_session_fixture.get_ids_container_model()
    response = await receive_alerts_from_ids_for_ensemble(alert_data=alert_data,db=db_session)
    response_json = json.loads(response.body.decode())
    print(response_json)
    assert response.status_code == 200
    assert response_json == {'content': f'Successfully pushed alerts for ensemble {mock_ensemble.name}'}

