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
client = TestClient(app)

@pytest.fixture
def db_session():
    mock_db = MagicMock()
    yield mock_db

@pytest.fixture
def mock_stream_metric_tasks():
    return AsyncMock()

@pytest.fixture
def client(db_session, mock_stream_metric_tasks):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_stream_metric_tasks] = lambda: mock_stream_metric_tasks
    with TestClient(app) as test_client:
        yield test_client



def test_setup_ensembles(client):
    ensemble_data = {
        "name": "Test Ensemble",
        "description": "Test Description",
        "technique": 1,
        "container_ids": [1, 2]
    }

    response = client.post("/ensemble/setup", json=ensemble_data)
    assert response.status_code == 200
    assert "content" in response.json()

@patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
@patch("app.models.ensemble.remove_ensemble", new_callable=MagicMock)
def test_remove_ensemble(mock_remove_ensemble, mock_get_ensemble_by_id, client):
    ensemble_id = 1
    mock_get_ensemble_by_id.return_value = Ensemble(id=ensemble_id, name="Test Ensemble")
    
    response = client.delete(f"/ensemble/remove/{ensemble_id}")
    assert response.status_code == 200
    assert "content" in response.json()

@patch("app.models.dataset.get_dataset_by_id", new_callable=MagicMock)
@patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
def test_start_static_container_analysis(mock_get_ensemble_by_id, mock_get_dataset_by_id, client):
    mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")
    mock_get_dataset_by_id.return_value = Dataset(id=1, name="Test Dataset")

    static_analysis_data = {
        "ensemble_id": 1,
        "dataset_id": 1
    }

    response = client.post("/ensemble/analysis/static", json=static_analysis_data)
    assert response.status_code == 200
    assert "content" in response.json()

@patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
def test_stop_analysis(mock_get_ensemble_by_id, client):
    mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")

    stop_data = {
        "ensemble_id": 1
    }

    response = client.post("/ensemble/analysis/stop", json=stop_data)
    assert response.status_code == 200
    assert "content" in response.json()

@patch("app.models.ids_container.get_container_by_id", new_callable=MagicMock)
@patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
def test_finished_analysis(mock_get_ensemble_by_id, mock_get_container_by_id, client):
    mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")
    mock_get_container_by_id.return_value = IdsContainer(id=1, name="Test Container")

    finished_data = {
        "ensemble_id": 1,
        "container_id": 1
    }

    response = client.post("/ensemble/analysis/finished", json=finished_data)
    assert response.status_code == 200
    assert "Successfully finished analysis" in response.text

@patch("app.models.ids_container.get_container_by_id", new_callable=MagicMock)
@patch("app.models.ensemble.get_ensemble_by_id", new_callable=MagicMock)
def test_publish_alerts(mock_get_ensemble_by_id, mock_get_container_by_id, client):
    mock_get_ensemble_by_id.return_value = Ensemble(id=1, name="Test Ensemble")
    mock_get_container_by_id.return_value = IdsContainer(id=1, name="Test Container")

    alert_data = {
        "container_id": 1,
        "ensemble_id": 1,
        "alerts": []
    }

    response = client.post("/ensemble/publish/alerts", json=alert_data)
    assert response.status_code == 200
    assert "Successfully pushed alerts" in response.text
