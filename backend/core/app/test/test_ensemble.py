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


# @patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
# def test_stop_analysis(mock_get_ensemble_by_id, client):
#     mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")

#     stop_data = {
#         "ensemble_id": 1
#     }

#     response = client.post("/ensemble/analysis/stop", json=stop_data)
#     assert response.status_code == 200
#     assert "content" in response.json()




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

# @patch("app.models.ids_container.get_container_by_id", new_callable=MagicMock)
# @patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
# def test_publish_alerts(mock_get_ensemble_by_id, mock_get_container_by_id, client):
#     mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")
#     mock_get_container_by_id.return_value = IdsContainer(id=1, name="Test Container")

#     alert_data = {
#         "container_id": 1,
#         "ensemble_id": 1,
#         "alerts": []
#     }

#     response = client.post("/ensemble/publish/alerts", json=alert_data)
#     assert response.status_code == 200
#     assert "Successfully pushed alerts" in response.text
