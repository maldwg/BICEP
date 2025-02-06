import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from app.main import app
from app.database import get_db
from app.models.configuration import Configuration
from app.database import Base
from app.routers.crud import *
from starlette.datastructures import UploadFile
from fastapi.responses import JSONResponse
import json
from app.models.ids_tool import IdsTool
from app.models.ids_container import IdsContainer
from app.test.fixtures import *



@pytest.mark.asyncio
async def test_add_new_dataset(db_session_fixture: DatabaseSessionFixture, mock_background_tasks):
    db_session = db_session_fixture.get_db_session()
    pcap_mock_file = MagicMock(spec=UploadFile)
    pcap_mock_file.filename = "data.pcap"
    pcap_mock_file.read = AsyncMock(return_value=open(f"{TESTS_BASE_DIR}/testfiles/sample_data.pcap","rb"))

    labels_mock_file = MagicMock(spec=UploadFile)
    labels_mock_file.filename = "labels.csv"
    labels_mock_file.read = AsyncMock(return_value=open(f"{TESTS_BASE_DIR}/testfiles/sample_data.csv","rb"))

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

@pytest.mark.asyncio
async def test_add_configuration(db_session_fixture: DatabaseSessionFixture, mock_background_tasks):
    db_session = db_session_fixture.get_db_session()
    config_mock_file = MagicMock(spec=UploadFile)
    config_mock_file.filename = "config.yaml"
    config_mock_file.read = AsyncMock(return_value=open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml","rb").read())

    # Prepare mock inputs
    mock_files = [config_mock_file]
    name = "Test Config"
    description = "A description for the configuration"

    response = await add_new_config(
        configuration=mock_files,
        name=name,
        description=description,
        db=db_session,
        background_tasks=mock_background_tasks,
    )
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {"message": "configuration added successfully"}

@pytest.mark.asyncio
async def test_get_all_configurations(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    result = await get_all_configs(db_session)

    assert len(result) == 2
    assert result[0]["name"] == "test-config 1"
    assert result[1]["file_type"] == "rule-set"


@pytest.mark.asyncio
async def test_get_all_configs_of_a_filetype(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    file_type = "rule-set" 
    response = await get_all_configs_of_a_filetype(file_type=file_type, db=db_session)
    mock_configuration_ruleset = db_session_fixture.get_ruleset_model()
    assert len(response) == 1
    assert response[0]["name"] == mock_configuration_ruleset.name


@pytest.mark.asyncio
async def test_get_all_configs_of_an_invalid_filetype(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    file_type = "invalid_type"
    expected_response = {"message": "wrong file type"}
    result = await get_all_configs_of_a_filetype(file_type=file_type, db=db_session)
    assert result == expected_response


@pytest.mark.asyncio
async def test_remove_config(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    config_id = 1
    result = await remove_config(id=config_id, db=db_session)
    assert result.status_code == 204


@pytest.mark.asyncio
async def test_get_all_datasets(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    response = await get_all_ds(db=db_session)

    assert len(response) == 2
    assert response[0]["name"] == "Test Dataset"
    assert response[1]["name"] == "Test Dataset 2"

@pytest.mark.asyncio
async def test_remove_dataset(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    dataset_id = 1
    result = await remove_dataset(id=dataset_id, db=db_session)

    assert result.status_code == 204

@pytest.mark.asyncio
async def test_get_all_ids_tools(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    result = await get_all_ids_tools(db=db_session)
    assert len(result) == 2
    assert result[0].name == "Suricata"
    assert result[1].name == "Slips"


@pytest.mark.asyncio
async def test_get_all_ids_container(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    response = await get_all_ids_container(db=db_session)
    assert len(response) == 1
    assert response[0].name == "container-0"
    assert response[0].description == "Test description"



@pytest.mark.asyncio
async def test_get_all_ids_container_not_assigned_to_an_ensemble(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()
    available_mock_container = AsyncMock(spec=IdsContainer)
    available_mock_container.id = 2
    available_mock_container.status = STATUS.IDLE.value
    available_mock_container.ids_tool_id = 1
    available_mock_container.description = "Test description 2"

    with patch("app.routers.crud.get_all_container", new_callable=MagicMock,return_value=[mock_container,available_mock_container]):
        response = await get_all_ids_container_not_assigned_to_an_ensemble(db=db_session)

    assert len(response) == 1
    assert response[0] == available_mock_container

@pytest.mark.asyncio
async def test_patch_container(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    container_update_data: IdsContainerUpdate = IdsContainerUpdate(
        id= 1,
        description= "new",
        configuration_id = 3,
        ruleset_id=2
    )
    response = await patch_container(container=container_update_data, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {'message': 'updated container successfully'}


@pytest.mark.asyncio
async def test_get_ensemble_techniques(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_ensemble_technique = db_session_fixture.get_ensemble_technique_model()
    response = await get_ensemble_techniques(db=db_session)

    assert len(response) == 1
    assert response[0] == mock_ensemble_technique


@pytest.mark.asyncio
async def test_get_ensembles(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_ensemble_ids = db_session_fixture.get_ensemble_ids_model()
    response = await get_ensembles(db=db_session)

    assert len(response) == 1
    assert response[0] == mock_ensemble_ids

@patch("app.models.ensemble.Ensemble.remove_container")
@patch("app.models.ensemble.Ensemble.add_container")
@pytest.mark.asyncio
async def test_patch_ensemble_add_and_remove_container(add_container_mock, remove_container_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    ensemble_update = EnsembleUpdate(
        id= 1,
        name="new-name",
        description= "new-description",
        technique_id= 1,
        container_ids= [2]
    )
    
    mock_response_remove = AsyncMock()
    mock_response_remove.status_code = 200
    mock_response_add = AsyncMock()
    mock_response_add.status_code = 200

    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.add_container.return_value = mock_response_add
    mock_ensemble.remove_container.return_value = mock_response_remove

    response = await patch_ensemble(ensmeble=ensemble_update, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {"messages": "successfully changed ensemble attributes"}


@patch("app.models.ensemble.Ensemble.remove_container")
@patch("app.models.ensemble.Ensemble.add_container")
@pytest.mark.asyncio
async def test_patch_ensemble_add_and_remove_container_failiure(add_container_mock, remove_container_mock, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    ensemble_update = EnsembleUpdate(
        id= 1,
        name="new-name",
        description= "new-description",
        technique_id= 1,
        container_ids= [2]
    )
    
    mock_response_remove = AsyncMock()
    mock_response_remove.status_code = 500
    mock_response_add = AsyncMock()
    mock_response_add.status_code = 500

    mock_ensemble = db_session_fixture.get_ensemble_model()
    mock_ensemble.add_container.return_value = mock_response_add
    mock_ensemble.remove_container.return_value = mock_response_remove

    response = await patch_ensemble(ensmeble=ensemble_update, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 500
    assert response_json == {"messages": "Failed to change ensemble attributes"}

@pytest.mark.asyncio
async def test_return_all_hosts(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_host = db_session_fixture.get_docker_host_system_model()
    response = await return_all_hosts(db=db_session)

    assert len(response) == 1
    assert response[0] == mock_host


@pytest.mark.asyncio
async def test_create_host(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    host_data = DockerHostCreationData(
        name="new-host",
        host="localhost",
        docker_port=2375
    )
    response = await create_host(host_data=host_data, db=db_session)
    response_json = json.loads(response.body.decode())
    assert response.status_code == 200
    assert response_json == {"message": "Successfully created host"}


@pytest.mark.asyncio
async def test_delete_host(db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    host_id = 1
    response = await delete_host(id=host_id, db=db_session)
    assert response.status_code == 204
