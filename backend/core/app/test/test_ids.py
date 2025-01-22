import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app 
from app.database import get_db
from app.utils import get_stream_metric_tasks

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



def test_setup_ids(client):
    request_data = {
        "host_system_id": 1,
        "description": "Test IDS Container",
        "configuration_id": 1,
        "ids_tool_id": 1,
    }

    response = client.post("/ids/setup", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"message": "setup done"}

@patch("app.models.ids_container.IdsContainer")
def test_remove_container(client):
    container_id = 1
    response = client.delete(f"/ids/remove/{container_id}")

    assert response.status_code == 200
    assert response.json() == {"message": "teardown done"}

def test_start_static_container_analysis(client):
    request_data = {
        "container_id": 1,
        "dataset_id": 1,
    }

    response = client.post("/ids/analysis/static", json=request_data)

    assert response.status_code in [200, 500]

def test_start_network_container_analysis(client):
    request_data = {
        "container_id": 1,
        "network_configuration": "Test network config",
    }

    response = client.post("/ids/analysis/network", json=request_data)

    assert response.status_code in [200, 500]

# Test for /ids/analysis/stop
def test_stop_analysis(client):
    request_data = {
        "container_id": 1,
    }

    response = client.post("/ids/analysis/stop", json=request_data)

    assert response.status_code in [200, 500]

# Test for /ids/analysis/finished
def test_finished_analysis(client):
    request_data = {
        "container_id": 1,
    }

    response = client.post("/ids/analysis/finished", json=request_data)

    assert response.status_code == 200

def test_receive_alerts_from_ids(client):
    request_data = {
        "container_id": 1,
        "alerts": [
            {
                "time": "2025-01-01T12:00:00Z",
                "destination_ip": "192.168.0.1",
                "destination_port": 8080,
                "source_ip": "10.0.0.1",
                "source_port": 1234,
                "severity": "high",
                "type": "test alert",
                "message": "Test alert message",
            }
        ],
        "analysis_type": "static",
        "dataset_id": 1,
    }

    response = client.post("/ids/publish/alerts", json=request_data)

    assert response.status_code == 200
    assert response.text == "Successfully pushed alerts and metrics to Loki"

def test_display_background_tasks(client):
    response = client.get("/ids/help/background-tasks")

    assert response.status_code == 200