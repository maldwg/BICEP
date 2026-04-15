from __future__ import annotations

import asyncio
import socket

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.docker_host_system import get_all_hosts, get_host_by_id
from app.models.metric_service import (
    get_all_metric_services,
    get_or_create_metric_service,
    serialize_metric_service,
    update_metric_service,
)
from app.models.metrics import MetricServiceRegistrationRequest
from app.utils import DOCKER_HOST_STATUS, METRIC_SERVICE_STATUS

router = APIRouter(prefix="/metric-services")


def _normalize_aliases(*values: str | None) -> set[str]:
    aliases: set[str] = set()
    for value in values:
        if not value:
            continue
        aliases.add(value.lower())
        try:
            _, _, ips = socket.gethostbyname_ex(value)
            aliases.update(ip.lower() for ip in ips)
        except Exception:
            continue
    return aliases


def _registration_mismatch_response() -> JSONResponse:
    return JSONResponse(
        {
            "error": (
                "Metric service registration could not be linked to the configured "
                "Docker host."
            )
        },
        status_code=400,
    )


async def _normalize_aliases_async(*values: str | None) -> set[str]:
    return await asyncio.to_thread(_normalize_aliases, *values)


async def _resolve_host_for_registration(db, registration: MetricServiceRegistrationRequest):
    reported_aliases = await _normalize_aliases_async(
        registration.name, registration.ip
    )
    hosts = await get_all_hosts(db)

    for host in hosts:
        expected_aliases = await asyncio.to_thread(host.resolve_host_aliases)
        if reported_aliases.intersection(expected_aliases):
            return host

    return None


async def _persist_metric_service_registration(host, registration, db):
    metric_service = await get_or_create_metric_service(
        db,
        host.id,
        name=registration.name,
        port=registration.port,
        status=METRIC_SERVICE_STATUS.REGISTERING.value,
        status_message="Metric service registered. Verifying health endpoint.",
    )

    is_healthy = await host._metric_service_healthcheck(registration.ip, registration.port)
    await update_metric_service(
        db,
        metric_service,
        name=registration.name,
        ip=registration.ip,
        port=registration.port,
        status=(
            METRIC_SERVICE_STATUS.AVAILABLE.value
            if is_healthy
            else METRIC_SERVICE_STATUS.UNAVAILABLE.value
        ),
        status_message=(
            "Metric service is healthy."
            if is_healthy
            else "Metric service registered but failed its healthcheck."
        ),
        registered_now=True,
    )

    host.status = (
        DOCKER_HOST_STATUS.AVAILABLE.value
        if is_healthy
        else DOCKER_HOST_STATUS.UNAVAILABLE.value
    )
    await db.commit()
    await db.refresh(host)

    return JSONResponse(
        {
            "message": "Metric service registered successfully.",
            "host_id": host.id,
            "metric_service": serialize_metric_service(metric_service),
        },
        status_code=200 if is_healthy else 202,
    )


@router.get("/all")
async def get_registered_metric_services(db=Depends(get_db)):
    metric_services = await get_all_metric_services(db)
    return [serialize_metric_service(metric_service) for metric_service in metric_services]


@router.post("/register")
async def register_metric_service(
    registration: MetricServiceRegistrationRequest,
    db=Depends(get_db),
):
    host = await _resolve_host_for_registration(db, registration)
    if host is None:
        return _registration_mismatch_response()

    return await _persist_metric_service_registration(host, registration, db)


@router.post("/register/{host_id}")
async def register_metric_service_for_host(
    host_id: int,
    registration: MetricServiceRegistrationRequest,
    db=Depends(get_db),
):
    host = await get_host_by_id(db, host_id)
    if host is None:
        return JSONResponse(
            {"error": f"Docker host with id {host_id} was not found."},
            status_code=404,
        )

    expected_aliases, reported_aliases = await asyncio.gather(
        asyncio.to_thread(host.resolve_host_aliases),
        _normalize_aliases_async(registration.name, registration.ip),
    )
    if not reported_aliases.intersection(expected_aliases):
        return _registration_mismatch_response()

    return await _persist_metric_service_registration(host, registration, db)
