import pytest
from docker import DockerClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.test.fixtures import *
from app.models.ids_container import *
from app.utils import STATUS, get_core_host

@pytest.fixture
def mock_ids_container():
    mock_host_system = DockerHostSystem(
        id = 1,
        name = "localhost",
        host = "localhost",
        docker_port = 2375
    )
    ids_container = IdsContainer(
        id = 1,
        name = "Test IDS",
        port = 8080,
        status = STATUS.IDLE.value,
        description = "Test Description",
        configuration_id = 1,
        ids_tool_id = 1,
        ruleset_id = 1,
        host_system_id = 1,
        host_system = mock_host_system
    )
    return ids_container

@pytest.mark.asyncio
async def test_is_busy(mock_ids_container: IdsContainer):
    mock_ids_container.status = STATUS.ACTIVE.value
    assert await mock_ids_container.is_busy() is True

@pytest.mark.asyncio
async def test_is_not_busy(mock_ids_container: IdsContainer):
    mock_ids_container.status = STATUS.IDLE.value
    assert await mock_ids_container.is_busy() is False


def test_get_container_http_url_localhost(mock_ids_container: IdsContainer):
    docker_host = mock_ids_container.get_container_http_url()
    core_host = get_core_host()
    docker_host = mock_ids_container.get_container_http_url()
    assert docker_host == f"http://{core_host}:{mock_ids_container.port}"

def test_get_container_http_url_core(mock_ids_container: IdsContainer):
    mock_ids_container.host_system.name = "Core"
    core_host = get_core_host()
    docker_host = mock_ids_container.get_container_http_url()
    assert docker_host == f"http://{core_host}:{mock_ids_container.port}"

def test_get_container_http_url_proper_host(mock_ids_container: IdsContainer):
    mock_ids_container.host_system.name = "proper_host"
    mock_ids_container.host_system.host = "my-custom-dns-name"
    docker_host = mock_ids_container.get_container_http_url()
    assert docker_host == f"http://{mock_ids_container.host_system.host}:{mock_ids_container.port}"



@pytest.mark.asyncio
async def test_update_container_existing( db_session_fixture: DatabaseSessionFixture):
    db_session = await db_session_fixture.get_db_session()
    mock_container = await db_session_fixture.get_ids_container_model()
    container_update = IdsContainerUpdate(id=mock_container.id, configuration_id=2, ruleset_id=3, description="123-Test")
    await update_container(db=db_session, container=container_update)
    
    assert mock_container is not None
    assert mock_container.configuration_id == 2
    assert mock_container.ruleset_id == 3
    assert mock_container.description=="123-Test"

@pytest.mark.asyncio
async def test_update_container_not_existing( db_session_fixture: DatabaseSessionFixture):
    db_session = await db_session_fixture.get_db_session()
    container_update = IdsContainerUpdate(id=999, configuration_id=2, ruleset_id=3, description="123-Test") 
    response = await update_container(db=db_session, container=container_update)
    
    assert response is None

@pytest.mark.asyncio
async def test_update_container_no_changes( db_session_fixture: DatabaseSessionFixture):
    db_session = await db_session_fixture.get_db_session()
    mock_container = await db_session_fixture.get_ids_container_model()
    mock_container is not None
    old_config_id =mock_container.configuration_id 
    old_ruleset_id = mock_container.ruleset_id 
    old_description =mock_container.description

    container_update = IdsContainerUpdate(id=mock_container.id, configuration_id=mock_container.configuration_id, ruleset_id=mock_container.ruleset_id, description=mock_container.description)
    await update_container(db=db_session, container=container_update)
    
    assert mock_container is not None
    assert mock_container.configuration_id == old_config_id
    assert mock_container.ruleset_id == old_ruleset_id
    assert mock_container.description==old_description
