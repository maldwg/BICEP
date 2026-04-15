import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.routers.monitoring import get_monitoring_metrics, get_historical_metrics
from app.models.ids_system import IdsSystem
from app.utils import STATUS


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_active_container():
    container = MagicMock(spec=IdsSystem)
    container.id = 1
    container.name = "test-container"
    container.status = STATUS.ACTIVE.value
    container.type = "NIDS"
    container.components = []
    return container


@pytest.fixture
def mock_active_cids():
    container = MagicMock(spec=IdsSystem)
    container.id = 12
    container.name = "Hamstring-39021"
    container.status = STATUS.ACTIVE.value
    container.type = "CIDS"

    sensor = MagicMock()
    sensor.id = 1201
    sensor.name = "bicep_cids_12_sensor-1"
    sensor.service_name = "sensor"
    sensor.role = "sensor"
    aggregator = MagicMock()
    aggregator.id = 1202
    aggregator.name = "bicep_cids_12_aggregator-1"
    aggregator.service_name = "aggregator"
    aggregator.role = "aggregator"
    container.components = [sensor, aggregator]
    return container


@pytest.mark.asyncio
async def test_get_monitoring_metrics_success(mock_db_session, mock_active_container):
    with patch(
        "app.routers.monitoring.get_all_container", new_callable=AsyncMock
    ) as mock_get_containers:
        mock_get_containers.return_value = [mock_active_container]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Mock responses for CPU and Memory queries
            # The function makes two calls sequentially
            cpu_response = MagicMock()
            cpu_response.status_code = 200
            cpu_response.json.return_value = {
                "data": {"result": [{"value": [1234567890, "0.5"]}]}
            }

            mem_response = MagicMock()
            mem_response.status_code = 200
            mem_response.json.return_value = {
                "data": {"result": [{"value": [1234567890, "100.0"]}]}
            }

            mock_client.get.side_effect = [cpu_response, mem_response]

            response = await get_monitoring_metrics(db=mock_db_session)
            mock_get_containers.assert_awaited_once_with(
                mock_db_session, include_deleted=False
            )
            assert response.status_code == 200
            content = response.body.decode()
            assert "test-container" in content
            assert "0.5" in content
            assert "100.0" in content


@pytest.mark.asyncio
async def test_get_monitoring_metrics_fail_prom(mock_db_session, mock_active_container):
    with patch(
        "app.routers.monitoring.get_all_container", new_callable=AsyncMock
    ) as mock_get_containers:
        mock_get_containers.return_value = [mock_active_container]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Prometheus down")

            response = await get_monitoring_metrics(db=mock_db_session)
            assert response.status_code == 200
            content = response.body.decode()
            # Should still return container info but with 0 usage
            assert "test-container" in content
            assert '"cpu_usage":0' in content.replace(" ", "")


@pytest.mark.asyncio
async def test_get_historical_metrics_success(mock_db_session, mock_active_container):
    with patch(
        "app.routers.monitoring.get_all_container", new_callable=AsyncMock
    ) as mock_get_containers:
        mock_get_containers.return_value = [mock_active_container]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            cpu_response = MagicMock()
            cpu_response.status_code = 200
            cpu_response.json.return_value = {
                "data": {"result": [{"values": [[100, "0.1"], [102, "0.2"]]}]}
            }

            mem_response = MagicMock()
            mem_response.status_code = 200
            mem_response.json.return_value = {
                "data": {"result": [{"values": [[100, "10"], [102, "20"]]}]}  # MB
            }

            mock_client.get.side_effect = [cpu_response, mem_response]

            response = await get_historical_metrics(
                start="1h", end=None, db=mock_db_session
            )
            mock_get_containers.assert_awaited_once_with(
                mock_db_session, include_deleted=True
            )
            assert response.status_code == 200
            content = response.body.decode()
            assert "test-container" in content
            assert "0.1" in content
            assert "20.0" in content


@pytest.mark.asyncio
async def test_get_historical_metrics_absolute_time(
    mock_db_session, mock_active_container
):
    with patch(
        "app.routers.monitoring.get_all_container", new_callable=AsyncMock
    ) as mock_get_containers:
        mock_get_containers.return_value = [mock_active_container]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Don't care about return values much, just that it runs
            mock_client.get.return_value = MagicMock(status_code=404)

            start_time = "2025-01-01T12:00:00Z"
            end_time = "2025-01-01T13:00:00Z"

            response = await get_historical_metrics(
                start=start_time, end=end_time, db=mock_db_session
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_monitoring_metrics_cids_uses_component_prefixes(
    mock_db_session, mock_active_cids
):
    with patch(
        "app.routers.monitoring.get_all_container", new_callable=AsyncMock
    ) as mock_get_containers:
        mock_get_containers.return_value = [mock_active_cids]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            cpu_response = MagicMock()
            cpu_response.status_code = 200
            cpu_response.json.return_value = {
                "data": {"result": [{"value": [1234567890, "2.5"]}]}
            }

            mem_response = MagicMock()
            mem_response.status_code = 200
            mem_response.json.return_value = {
                "data": {"result": [{"value": [1234567890, "512.0"]}]}
            }

            mock_client.get.side_effect = [cpu_response, mem_response]

            response = await get_monitoring_metrics(db=mock_db_session)

            assert response.status_code == 200
            content = response.body.decode()
            assert "Hamstring-39021" in content
            assert "2.5" in content
            assert "512.0" in content

            first_query = mock_client.get.call_args_list[0].kwargs["params"]["query"]
            assert "sum(container_cpu_usage" in first_query
            assert "bicep_cids_12_sensor" in first_query
            assert "bicep_cids_12_aggregator" in first_query
            assert "Hamstring-39021" not in first_query


@pytest.mark.asyncio
async def test_get_historical_metrics_cids_uses_component_prefixes(
    mock_db_session, mock_active_cids
):
    with patch(
        "app.routers.monitoring.get_all_container", new_callable=AsyncMock
    ) as mock_get_containers:
        mock_get_containers.return_value = [mock_active_cids]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            cpu_response = MagicMock()
            cpu_response.status_code = 200
            cpu_response.json.return_value = {
                "data": {"result": [{"values": [[100, "1.1"], [102, "1.3"]]}]}
            }

            mem_response = MagicMock()
            mem_response.status_code = 200
            mem_response.json.return_value = {
                "data": {"result": [{"values": [[100, "256"], [102, "384"]]}]}
            }

            mock_client.get.side_effect = [cpu_response, mem_response]

            response = await get_historical_metrics(
                start="1h", end=None, db=mock_db_session
            )

            assert response.status_code == 200
            content = response.body.decode()
            assert "Hamstring-39021" in content
            assert "1.1" in content
            assert "384.0" in content

            first_query = mock_client.get.call_args_list[0].kwargs["params"]["query"]
            assert "sum(container_cpu_usage" in first_query
            assert "bicep_cids_12_sensor" in first_query
            assert "bicep_cids_12_aggregator" in first_query
            assert "Hamstring-39021" not in first_query


@pytest.mark.asyncio
async def test_get_historical_metrics_expands_cids_components(
    mock_db_session, mock_active_cids
):
    with patch(
        "app.routers.monitoring.get_all_container", new_callable=AsyncMock
    ) as mock_get_containers:
        mock_get_containers.return_value = [mock_active_cids]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            overall_cpu_response = MagicMock()
            overall_cpu_response.status_code = 200
            overall_cpu_response.json.return_value = {
                "data": {"result": [{"values": [[100, "1.1"], [102, "1.3"]]}]}
            }

            overall_mem_response = MagicMock()
            overall_mem_response.status_code = 200
            overall_mem_response.json.return_value = {
                "data": {"result": [{"values": [[100, "256"], [102, "384"]]}]}
            }

            sensor_cpu_response = MagicMock()
            sensor_cpu_response.status_code = 200
            sensor_cpu_response.json.return_value = {
                "data": {"result": [{"values": [[100, "0.4"], [102, "0.5"]]}]}
            }

            sensor_mem_response = MagicMock()
            sensor_mem_response.status_code = 200
            sensor_mem_response.json.return_value = {
                "data": {"result": [{"values": [[100, "80"], [102, "84"]]}]}
            }

            aggregator_cpu_response = MagicMock()
            aggregator_cpu_response.status_code = 200
            aggregator_cpu_response.json.return_value = {
                "data": {"result": [{"values": [[100, "0.7"], [102, "0.8"]]}]}
            }

            aggregator_mem_response = MagicMock()
            aggregator_mem_response.status_code = 200
            aggregator_mem_response.json.return_value = {
                "data": {"result": [{"values": [[100, "176"], [102, "300"]]}]}
            }

            mock_client.get.side_effect = [
                overall_cpu_response,
                overall_mem_response,
                sensor_cpu_response,
                sensor_mem_response,
                aggregator_cpu_response,
                aggregator_mem_response,
            ]

            response = await get_historical_metrics(
                start="1h", end=None, expanded_ids=[12], db=mock_db_session
            )

            assert response.status_code == 200
            payload = json.loads(response.body.decode())
            content = payload["content"]

            assert "Hamstring-39021" in content
            assert "Hamstring-39021 :: sensor" in content
            assert "Hamstring-39021 :: aggregator" in content
            assert content["Hamstring-39021 :: sensor"]["is_component"] is True
            assert content["Hamstring-39021 :: sensor"]["parent_id"] == 12
            assert content["Hamstring-39021 :: sensor"]["raw_name"] == "bicep_cids_12_sensor-1"

            sensor_query = mock_client.get.call_args_list[2].kwargs["params"]["query"]
            aggregator_query = mock_client.get.call_args_list[4].kwargs["params"]["query"]
            assert 'name="bicep_cids_12_sensor-1"' in sensor_query
            assert 'name="bicep_cids_12_aggregator-1"' in aggregator_query
