import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.routers.monitoring import get_monitoring_metrics, get_historical_metrics
from app.models.ids_container import IdsContainer
from app.utils import STATUS
from datetime import datetime


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_active_container():
    container = MagicMock(spec=IdsContainer)
    container.id = 1
    container.name = "test-container"
    container.status = STATUS.ACTIVE.value
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
