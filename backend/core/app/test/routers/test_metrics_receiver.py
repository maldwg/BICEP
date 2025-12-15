import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.routers.metrics_receiver import receive_metrics
from app.models.metrics import MetricPushRequest


@pytest.mark.asyncio
async def test_receive_metrics_success():
    metrics_data = MetricPushRequest(
        container_id=1,
        container_name="test-container",
        cpu_usage=0.5,
        memory_usage=100.0,  # MB
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        response = await receive_metrics(metrics_data)
        assert response.status_code == 200
        assert b"success" in response.body


@pytest.mark.asyncio
async def test_receive_metrics_failure_gateway():
    metrics_data = MetricPushRequest(
        container_id=1,
        container_name="test-container",
        cpu_usage=0.5,
        memory_usage=100.0,
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.post.return_value = mock_response

        response = await receive_metrics(metrics_data)
        assert response.status_code == 500
        assert b"failed" in response.body


@pytest.mark.asyncio
async def test_receive_metrics_exception():
    metrics_data = MetricPushRequest(
        container_id=1,
        container_name="test-container",
        cpu_usage=0.5,
        memory_usage=100.0,
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = Exception("Gateway unreachable")

        response = await receive_metrics(metrics_data)
        assert response.status_code == 500
        assert b"error" in response.body
