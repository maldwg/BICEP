import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from app.main import app
from app.database import get_db
from app.models.configuration import Configuration
from sqlalchemy.orm import Session
from app.database import Base
from app.routers.crud import *
from starlette.datastructures import UploadFile
from fastapi.responses import JSONResponse
import json
from app.models.ids_tool import IdsTool
from app.models.ids_container import IdsContainer

TESTS_BASE_DIR = "./backend/core/app/test"

@pytest.fixture
def mock_background_tasks():
    """
    Mock the BackgroundTasks instance.
    """
    tasks = MagicMock(spec=set())
    tasks.add_task = MagicMock()
    return tasks


@pytest.fixture
def db_session():
    mock_db = MagicMock()
    yield mock_db


@pytest.mark.asyncio
@patch("app.routers.crud.calculate_and_add_dataset", new_callable=MagicMock)
async def test_add_new_dataset(mock_add_dataset, db_session, mock_background_tasks):

    pcap_mock_file = MagicMock(spec=UploadFile)
    pcap_mock_file.filename = "data.pcap"
    pcap_mock_file.read = AsyncMock(return_value=open(f"{TESTS_BASE_DIR}/testfiles/sample_data.pcap","rb"))

    labels_mock_file = MagicMock(spec=UploadFile)
    labels_mock_file.filename = "labels.csv"
    labels_mock_file.read = AsyncMock(return_value=open(f"{TESTS_BASE_DIR}/testfiles/sample_data.csv","rb"))

    # Call the endpoint
    response = await add_new_dataset(
        configuration=[pcap_mock_file, labels_mock_file],
        name="New dataset",
        description="Description",
        db=db_session,
        background_tasks=mock_background_tasks,
    )
    response_json = json.loads(response.body.decode())
    
    assert response.status_code == 200
    assert response_json == {"message": "configuration added successfully"}

@patch("app.routers.crud.add_config", new_callable=MagicMock)
@pytest.mark.asyncio
async def test_add_configuration(add_config_mock,db_session, mock_background_tasks):
    config_mock_file = MagicMock(spec=UploadFile)
    config_mock_file.filename = "config.yaml"
    config_mock_file.read = AsyncMock(return_value=open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml","rb").read())

    # Prepare mock inputs
    mock_files = [config_mock_file]
    name = "Test Config"
    description = "A description for the configuration"

    expected_response = JSONResponse(
        content={"message": "configuration added successfully"},
        status_code=200,
    )
    result = await add_new_config(
        configuration=mock_files,
        name=name,
        description=description,
        db=db_session,
        background_tasks=mock_background_tasks,
    )
    assert result.status_code == 200
    assert result.body == expected_response.body

@patch("app.routers.crud.get_all_configurations", new_callable=MagicMock)
@pytest.mark.asyncio
async def test_get_all_configurations(get_all_confgis_mock,db_session):
    get_all_confgis_mock.return_value= [
        Configuration(
            id = 0,
            name = "TestConfig1",
            configuration = open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml","rb").read(),
            file_type = "cofniguration",
            description = "Test config"
        ),
        Configuration(
            id = 1,
            name = "TestConfig2",
            configuration = open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml","rb").read(),
            file_type = "rule-set",
            description = "Test Ruleset"
        )
    ]

    # Call the function being tested
    result = await get_all_configs(db_session)

    # Assertions
    assert len(result) == 2
    assert result[0]["name"] == "TestConfig1"
    assert result[1]["file_type"] == "rule-set"


@patch("app.routers.crud.get_all_configurations_by_type", new_callable=MagicMock)
@pytest.mark.asyncio
async def test_get_all_configs_of_a_filetype(get_all_configs_mock, db_session):
    get_all_configs_mock.return_value = [
        Configuration(
            id=1,
            name="TestConfig2",
            configuration=open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml", "rb").read(),
            file_type="rule-set",
            description="Test Ruleset"
        )
    ]
    file_type = "rule-set" 
    expected_response = [
        {"id": 1, "name": "TestConfig2", "file_type": "rule-set", "description": "Test Ruleset"}
    ]
    result = await get_all_configs_of_a_filetype(file_type=file_type, db=db_session)
    assert len(result) == 1
    assert result[0]["name"] == expected_response[0]["name"]


@pytest.mark.asyncio
async def test_get_all_configs_of_an_invalid_filetype(db_session):
    file_type = "invalid_type"
    expected_response = {"message": "wrong file type"}
    result = await get_all_configs_of_a_filetype(file_type=file_type, db=db_session)
    assert result == expected_response


@patch("app.routers.crud.remove_configuration_by_id")
@pytest.mark.asyncio
async def test_remove_config(remove_config_mock, db_session):
    config_id = 1
    result = await remove_config(id=config_id, db=db_session)
    assert result.status_code == 204
    remove_config_mock.assert_called_once()


@patch("app.routers.crud.get_all_datasets")
@pytest.mark.asyncio
async def test_get_all_datasets(get_all_ds_mock,db_session):
    # Setup mock return data
    get_all_ds_mock.return_value = [

        Dataset(
            id = 0,
            name = "Test DS 0",
            pcap_file_path = "/test/path",
            labels_file_path = "/test/path",
            description = "DS 0",
            ammount_benign = 1000,
            ammount_malicious = 250
        ),
        Dataset(
            id = 1,
            name = "Test DS 1",
            pcap_file_path = "/test/path",
            labels_file_path = "/test/path",
            description = "DS 1",
            ammount_benign = 500,
            ammount_malicious = 60
        )
    ]

    # Call the function being tested
    result = await get_all_ds(db=db_session)

    # Assertions
    assert len(result) == 2
    assert result[0]["name"] == "Test DS 0"
    assert result[1]["description"] == "DS 1"

@patch("app.routers.crud.remove_dataset_by_id")
@pytest.mark.asyncio
async def test_remove_dataset(remove_ds_mock, db_session):
    dataset_id = 1
    result = await remove_dataset(id=dataset_id, db=db_session)

    assert result.status_code == 204
    remove_ds_mock.assert_called_once()

@patch("app.routers.crud.get_all_tools")
@pytest.mark.asyncio
async def test_get_all_ids_tools(tools_mock, db_session):
    tools_mock.return_value = [
        IdsTool(
            id = 0,
            name= "Suricata",
            ids_type = "NIDS",
            analysis_method = "signature-based",
            requires_ruleset = True,
            image_name = "suricata-dockerized",
            image_tag = "latest"
        ),
        IdsTool(
            id = 1,
            name= "Slips",
            ids_type = "NIDS",
            analysis_method = "anomaly-based",
            requires_ruleset = False,
            image_name = "slips-dockerized",
            image_tag = "latest"
        )
    ]
    result = await get_all_ids_tools(db=db_session)
    assert len(result) == 2
    assert result[0].name == "Suricata"
    assert result[1].image_name == "slips-dockerized"

@patch("app.routers.crud.get_all_container")
@pytest.mark.asyncio
async def test_get_all_ids_container(container_mock, db_session):
    container_mock.return_value = [
        IdsContainer(
            id = 0,
            name = "container-0",
            port = 1234,
            status = "ACTIVE",
            description = "container 0 description",
            stream_metric_task_id = None,
            configuration_id = 1,
            ids_tool_id = 2,
            ruleset_id = 0,
            host_system_id = 0
        )
    ]

    # Call the function being tested
    result = await get_all_ids_container(db=db_session)

    # Assertions
    assert len(result) == 1
    assert result[0].name == "container-0"
    assert result[0].description == "container 0 description"

