import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.metrics import MetricServiceRegistrationRequest
from app.routers.metric_services import (
    register_metric_service,
    register_metric_service_for_host,
)


@pytest.mark.asyncio
async def test_register_metric_service_success():
    host = MagicMock()
    host.id = 1
    host.status = "unavailable"
    host.resolve_host_aliases.return_value = {"worker.example", "10.0.0.5"}
    host._metric_service_healthcheck = AsyncMock(return_value=True)

    metric_service = MagicMock()
    metric_service.id = 7
    metric_service.host_system_id = 1
    metric_service.name = "worker.example"
    metric_service.ip = "10.0.0.5"
    metric_service.port = 18080
    metric_service.status = "available"
    metric_service.status_message = "Metric service is healthy."
    metric_service.last_registration_at = "2025-01-01T00:00:00"

    payload = MetricServiceRegistrationRequest(
        name="worker.example", ip="10.0.0.5", port=18080
    )

    with patch(
        "app.routers.metric_services.get_all_hosts", new_callable=AsyncMock
    ) as mock_get_hosts:
        mock_get_hosts.return_value = [host]

        with patch(
            "app.routers.metric_services.get_or_create_metric_service",
            new_callable=AsyncMock,
        ) as mock_get_or_create:
            mock_get_or_create.return_value = metric_service

            with patch(
                "app.routers.metric_services.update_metric_service",
                new_callable=AsyncMock,
            ) as mock_update:
                mock_update.return_value = metric_service

                db = AsyncMock()
                response = await register_metric_service(payload, db=db)
                assert response.status_code == 200
                assert b"registered successfully" in response.body
                assert host.status == "available"


@pytest.mark.asyncio
async def test_register_metric_service_for_host_rejects_mismatch():
    host = MagicMock()
    host.id = 1
    host.resolve_host_aliases.return_value = {"worker.example", "10.0.0.5"}

    payload = MetricServiceRegistrationRequest(
        name="wrong-host", ip="10.1.0.9", port=18080
    )

    with patch(
        "app.routers.metric_services.get_host_by_id", new_callable=AsyncMock
    ) as mock_get_host:
        mock_get_host.return_value = host

        with patch(
            "app.routers.metric_services.get_or_create_metric_service",
            new_callable=AsyncMock,
        ) as mock_get_or_create:
            with patch(
                "app.routers.metric_services.update_metric_service",
                new_callable=AsyncMock,
            ) as mock_update:
                response = await register_metric_service_for_host(
                    1, payload, db=AsyncMock()
                )
                assert response.status_code == 400
                assert b"could not be linked" in response.body
                mock_get_or_create.assert_not_awaited()
                mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_metric_service_for_host_success():
    host = MagicMock()
    host.id = 2
    host.status = "unavailable"
    host.resolve_host_aliases.return_value = {"192.168.1.50", "remote-worker"}
    host._metric_service_healthcheck = AsyncMock(return_value=True)

    metric_service = MagicMock()
    metric_service.id = 9
    metric_service.host_system_id = 2
    metric_service.name = "bicep-metric-service"
    metric_service.ip = "192.168.1.50"
    metric_service.port = 20080
    metric_service.status = "available"
    metric_service.status_message = "Metric service is healthy."
    metric_service.last_registration_at = "2025-01-01T00:00:00"

    payload = MetricServiceRegistrationRequest(
        name="bicep-metric-service", ip="192.168.1.50", port=20080
    )

    with patch(
        "app.routers.metric_services.get_host_by_id", new_callable=AsyncMock
    ) as mock_get_host:
        mock_get_host.return_value = host

        with patch(
            "app.routers.metric_services.get_or_create_metric_service",
            new_callable=AsyncMock,
        ) as mock_get_or_create:
            mock_get_or_create.return_value = metric_service

            with patch(
                "app.routers.metric_services.update_metric_service",
                new_callable=AsyncMock,
            ) as mock_update:
                mock_update.return_value = metric_service

                response = await register_metric_service_for_host(
                    2, payload, db=AsyncMock()
                )

                assert response.status_code == 200
                assert b"registered successfully" in response.body
                assert host.status == "available"
