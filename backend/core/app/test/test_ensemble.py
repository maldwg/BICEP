import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app  # Replace with the actual import for your FastAPI app
from app.models.ensemble import Ensemble
from app.models.ids_container import IdsContainer
from app.models.dataset import Dataset
from app.utils import STATUS, ANALYSIS_STATUS
from app.validation.models import EnsembleCreate, StaticAnalysisData, NetworkAnalysisData, stop_analysisData, AnalysisFinishedData, AlertData
from app.database import get_db
from app.utils import get_stream_metric_tasks
from app.routers.ensemble import *
from fastapi.responses import JSONResponse

@pytest.fixture
def db_session():
    mock_db = MagicMock()
    yield mock_db

@pytest.fixture
def mock_stream_metric_tasks():
    return AsyncMock()

@patch("app.models.ensemble.add_ensemble")
@patch("app.models.ensemble.Ensemble.add_container")
@pytest.mark.asyncio
async def test_setup_ensembles(_,add_container_mock,db_session):
    ensemble_data: EnsembleCreate = EnsembleCreate(
        name = "ensemble1",
        description="ensemble-test",
        technique= 0,
        container_ids= [0,1]
    )
    add_container_mock.return_value = JSONResponse(content="Successfully added", status_code = 200)
    response = await setup_ensembles(ensembleData=ensemble_data,db=db_session)
    response_json = json.loads(response.body.decode())
    # Ensemble is None because the db transaction is only mocked there is no ID assignment to the Ensemble
    expected_content = [
        {'content': 'successfully added container 0 to ensemble None', 'status_code': 200}, 
        {'content': 'successfully added container 1 to ensemble None', 'status_code': 200}
    ]
    assert response.status_code == 200
    assert expected_content == response_json["content"]

# @patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
# @patch("app.models.ensemble.remove_ensemble", new_callable=MagicMock)
# def test_remove_ensemble(mock_remove_ensemble, mock_get_ensemble_by_id, client):
#     ensemble_id = 1
#     mock_get_ensemble_by_id.return_value = Ensemble(id=ensemble_id, name="Test Ensemble")
    
#     response = client.delete(f"/ensemble/remove/{ensemble_id}")
#     assert response.status_code == 200
#     assert "content" in response.json()

# @patch("app.models.dataset.get_dataset_by_id", new_callable=MagicMock)
# @patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
# def test_start_static_container_analysis(mock_get_ensemble_by_id, mock_get_dataset_by_id, client):
#     mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")
#     mock_get_dataset_by_id.return_value = Dataset(id=1, name="Test Dataset")

#     static_analysis_data = {
#         "ensemble_id": 1,
#         "dataset_id": 1
#     }

#     response = client.post("/ensemble/analysis/static", json=static_analysis_data)
#     assert response.status_code == 200
#     assert "content" in response.json()

# @patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
# def test_stop_analysis(mock_get_ensemble_by_id, client):
#     mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")

#     stop_data = {
#         "ensemble_id": 1
#     }

#     response = client.post("/ensemble/analysis/stop", json=stop_data)
#     assert response.status_code == 200
#     assert "content" in response.json()

# @patch("app.models.ids_container.get_container_by_id", new_callable=MagicMock)
# @patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
# def test_finished_analysis(mock_get_ensemble_by_id, mock_get_container_by_id, client):
#     mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")
#     mock_get_container_by_id.return_value = IdsContainer(id=1, name="Test Container")

#     finished_data = {
#         "ensemble_id": 1,
#         "container_id": 1
#     }

#     response = client.post("/ensemble/analysis/finished", json=finished_data)
#     assert response.status_code == 200
#     assert "Successfully finished analysis" in response.text

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
