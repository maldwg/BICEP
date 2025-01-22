import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.database import get_db

TESTS_BASE_DIR = "./backend/core/app/test"


@pytest.fixture
def db_session():
    mock_db = MagicMock()
    yield mock_db

@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client

def test_get_all_configs(client, db_session):
    db_session.return_value.get_all_configurations.return_value = []

    response = client.get("/crud/configuration/all")

    assert response.status_code == 200
    assert response.json() == []

def test_add_new_config(client):
    file_content = b"dummy file content"

    response = client.post(
        "/crud/configuration/add",
        data={
            "name": "Test Config",
            "description": "Test Description",
            "file_type": "json",
        },
        files={"configuration": ("test_file.json", file_content)},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "configuration added successfully"}

def test_remove_config(client, db_session):
    response = client.delete("/crud/configuration/1")
    assert response.status_code == 204

def test_get_all_datasets(client, db_session):
    db_session.return_value.get_all_datasets.return_value = []

    response = client.get("/crud/dataset/all")

    assert response.status_code == 200
    assert response.json() == []

# def test_add_new_dataset(client):
#     # Define paths to test files
#     pcap_path = TESTS_BASE_DIR + "/testfiles/sample_data.pcap"
#     labels_path = TESTS_BASE_DIR + "/testfiles/sample_data.csv"

#     # Open the files in binary read mode
#     with open(pcap_path, "rb") as pcap_file, open(labels_path, "rb") as labels_file:
#         response = client.post(
#             "/crud/dataset/add",
#             data={
#                 "name": "Test Dataset",
#                 "description": "Test Description",
#             },
#             files={
#                 "configuration": [
#                     ("test_file.pcap", pcap_file, "application/octet-stream"),
#                     ("test_data.csv", labels_file, "text/plain"),
#                 ]
#             },
#         )

#     assert response.status_code == 200
#     assert response.json() == {"message": "configuration added successfully"}

def test_remove_dataset(client):
    response = client.delete("/crud/dataset/1")

    assert response.status_code == 200