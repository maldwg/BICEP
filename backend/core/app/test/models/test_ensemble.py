import pytest
from docker import DockerClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.test.fixtures import *
from app.models.ensemble import *
from app.utils import STATUS


@pytest.fixture
def mock_ensemble():
    ensemble = Ensemble(
        id = 1,
        name = "Test Ensemble",
        technique_id = 1,
        status = STATUS.IDLE.value,
        description =   "Test Description",
        current_analysis_id = None
    )
    return ensemble

from requests.models import Response
@patch("app.models.ids_container.IdsContainer.get_container_http_url")
@pytest.mark.asyncio
async def test_add_container(get_container_mock, mock_ensemble: Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()
    container_mock_url = "http://mock-container-url"
    get_container_mock.return_value = container_mock_url

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_response = Response()
        mock_response.status_code = 200
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        response = await mock_ensemble.add_container(container_id=mock_container.id,db=db_session)
        assert response.status_code == 200



@patch("app.models.ids_container.IdsContainer.get_container_http_url")
@pytest.mark.asyncio
async def test_add_container_failiure(get_container_mock,  mock_ensemble: Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()

    container_mock_url = "http://mock-container-url"
    get_container_mock.return_value = container_mock_url

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_response = Response()
        mock_response.status_code = 400
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        response = await mock_ensemble.add_container(container_id=mock_container.id,db=db_session)
        assert response.status_code == 400

@patch("app.models.ensemble.deregister_container_from_ensemble")
@pytest.mark.asyncio
async def test_remove_container(deregister_mock, mock_ensemble: Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 200
    deregister_mock.return_value = mock_response
    response = await mock_ensemble.remove_container(mock_container.id, db_session)
    assert response.status_code == 200

@patch("app.models.ensemble.deregister_container_from_ensemble")
@pytest.mark.asyncio
async def test_remove_container_failiure(deregister_mock, mock_ensemble: Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()
    mock_response = AsyncMock(spec=HTTPResponse)
    mock_response.status_code = 400
    deregister_mock.return_value = mock_response
    response = await mock_ensemble.remove_container(mock_container.id, db_session)
    assert response.status_code == 400

def test_get_containers(mock_ensemble: Ensemble,db_session_fixture:DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_ids_containers = [db_session_fixture.get_ids_container_model()]
    container_list = mock_ensemble.get_containers(db=db_session)
    assert container_list == mock_ids_containers


@pytest.mark.asyncio
async def test_start_static_analysis(mock_ensemble:Ensemble, db_session_fixture:DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_dataset = db_session_fixture.get_dataset_model()
    mock_container = db_session_fixture.get_ids_container_model()

    mock_container_response = AsyncMock(spec=HTTPResponse)
    mock_container_response.status_code = 200
    mock_container.start_static_analysis.return_value = mock_container_response
    mock_dataset.read_pcap_file = AsyncMock(return_value=b"mocked pcap content")
    mock_ensemble.get_containers = MagicMock(return_value=[mock_container])

    responses = await mock_ensemble.start_static_analysis(mock_dataset, db_session)
    assert responses[0].status_code == 200
    assert json.loads(responses[0].body.decode()) == { "message": "container 1 - static analysis for ensemble 1 triggered" }

@pytest.mark.asyncio
async def test_start_static_analysis_failiure(mock_ensemble:Ensemble, db_session_fixture:DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_dataset = db_session_fixture.get_dataset_model()
    mock_container = db_session_fixture.get_ids_container_model()

    mock_container_response = AsyncMock(spec=HTTPResponse)
    mock_container_response.status_code = 500
    mock_container.start_static_analysis.return_value = mock_container_response
    mock_dataset.read_pcap_file = AsyncMock(return_value=b"mocked pcap content")
    mock_ensemble.get_containers = MagicMock(return_value=[mock_container])

    responses = await mock_ensemble.start_static_analysis(mock_dataset, db_session)
    assert responses[0].status_code == 500
    assert json.loads(responses[0].body.decode()) == { "error": "container 1 - static analysis for ensemble 1 could not be triggered" }

@pytest.mark.asyncio
async def test_start_network_analysis(mock_ensemble:Ensemble, db_session_fixture:DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    network_analysis_data = NetworkAnalysisData(
        container_id = None,
        ensemble_id = 1
    )
    mock_container = db_session_fixture.get_ids_container_model()

    mock_container_response = AsyncMock(spec=HTTPResponse)
    mock_container_response.status_code = 200
    mock_container.start_network_analysis.return_value = mock_container_response
    mock_ensemble.get_containers = MagicMock(return_value=[mock_container])

    responses = await mock_ensemble.start_network_analysis(network_analysis_data, db_session)
    assert responses[0].status_code == 200
    assert json.loads(responses[0].body.decode()) == { "message": "container 1 - network analysis for ensemble 1 triggered" }

@pytest.mark.asyncio
async def test_start_network_analysis_failiure(mock_ensemble:Ensemble, db_session_fixture:DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    network_analysis_data = NetworkAnalysisData(
        container_id = None,
        ensemble_id = 1
    )
    mock_container = db_session_fixture.get_ids_container_model()

    mock_container_response = AsyncMock(spec=HTTPResponse)
    mock_container_response.status_code = 500
    mock_container.start_network_analysis.return_value = mock_container_response
    mock_ensemble.get_containers = MagicMock(return_value=[mock_container])

    responses = await mock_ensemble.start_network_analysis(network_analysis_data, db_session)
    assert responses[0].status_code == 500
    assert json.loads(responses[0].body.decode()) == { "error": "container 1 - network analysis for ensemble 1 could not be triggered" }


@pytest.mark.asyncio
async def test_stop_analysis(mock_ensemble:Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()

    mock_ensemble.get_containers = MagicMock(return_value=[mock_container])
    container_mock_response = AsyncMock(spec=HTTPResponse)
    container_mock_response.status_code = 200
    mock_container.stop_analysis.return_value = container_mock_response

    responses = await mock_ensemble.stop_analysis(db=db_session)
    assert responses[0].status_code == 200
    assert json.loads(responses[0].body.decode()) == {"message": f"Analysis for container {mock_container.id} successfully stopped"}


@pytest.mark.asyncio
async def test_stop_analysis_failiure(mock_ensemble:Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()

    mock_ensemble.get_containers = MagicMock(return_value=[mock_container])
    container_mock_response = AsyncMock(spec=HTTPResponse)
    container_mock_response.status_code = 500
    mock_container.stop_analysis.return_value = container_mock_response

    responses = await mock_ensemble.stop_analysis(db=db_session)
    assert responses[0].status_code == 500
    assert json.loads(responses[0].body.decode()) == {"error": f"Analysis for container {mock_container.id} could not be stopped"}


@pytest.mark.asyncio
async def test_container_is_last_one_running_in_ensemble_with_one_container(mock_ensemble: Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()
    assert await mock_ensemble.container_is_last_one_running(mock_container, db=db_session) is True

@pytest.mark.asyncio
async def test_container_is_last_one_running(mock_ensemble: Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()
    second_mock_container = MagicMock(spec=IdsContainer)
    second_mock_container.id = 2
    second_mock_container.is_busy = AsyncMock(return_value=False)
    mock_ensemble.get_containers = MagicMock(return_value=[mock_container, second_mock_container])
    assert await mock_ensemble.container_is_last_one_running(mock_container, db=db_session) is True

@pytest.mark.asyncio
async def test_container_is_not_last_one_running(mock_ensemble: Ensemble, db_session_fixture: DatabaseSessionFixture):
    db_session = db_session_fixture.get_db_session()
    mock_container = db_session_fixture.get_ids_container_model()
    second_mock_container = MagicMock(spec=IdsContainer)
    second_mock_container.id = 2
    second_mock_container.is_busy = AsyncMock(return_value=True)
    mock_ensemble.get_containers = MagicMock(return_value=[mock_container, second_mock_container])
    assert await mock_ensemble.container_is_last_one_running(mock_container, db=db_session) is False