from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.database import get_db
from app.models.ids_system import get_all_container
from app.prometheus import (
    RESOURCE_QUERY_MODE_EXACT,
    build_resource_metric_query,
    build_resource_query_spec_for_ids_system,
)
from app.utils import STATUS
from app.logger import LOGGER
import httpx
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/monitoring")


def _get_prometheus_url() -> str:
    prometheus_url = os.environ.get("PROMETHEUS_URL", "prometheus:9090")
    if not prometheus_url.startswith("http://") and not prometheus_url.startswith(
        "https://"
    ):
        prometheus_url = f"http://{prometheus_url}"
    return prometheus_url


async def _query_range_series(
    client: httpx.AsyncClient,
    prometheus_url: str,
    query: str | None,
    start_timestamp: float,
    end_timestamp: float,
    step: str,
) -> tuple[list[float], list[float]]:
    if not query:
        return [], []

    response = await client.get(
        f"{prometheus_url}/api/v1/query_range",
        params={
            "query": query,
            "start": start_timestamp,
            "end": end_timestamp,
            "step": step,
        },
        timeout=10.0,
    )

    if response.status_code != 200:
        return [], []

    data = response.json()
    results = data.get("data", {}).get("result", [])
    if not results:
        return [], []

    values = results[0].get("values", [])
    return [float(ts) for ts, _ in values], [float(val) for _, val in values]


def _build_historical_entry(
    *,
    entry_id: int,
    name: str,
    timestamps: list[float],
    cpu_values: list[float],
    memory_values: list[float],
    entry_type: str | None,
    is_component: bool,
    parent_id: int | None = None,
    parent_name: str | None = None,
    role: str | None = None,
    raw_name: str | None = None,
) -> dict:
    return {
        "id": entry_id,
        "name": name,
        "display_name": name,
        "raw_name": raw_name or name,
        "timestamps": timestamps,
        "cpu": cpu_values,
        "memory": memory_values,
        "type": entry_type,
        "is_component": is_component,
        "parent_id": parent_id,
        "parent_name": parent_name,
        "role": role,
    }


@router.get("/metrics")
async def get_monitoring_metrics(db=Depends(get_db)):
    """
    Get real-time metrics for all active IDS containers.
    """
    containers = await get_all_container(db, include_deleted=False)
    metrics_data = []

    prometheus_url = _get_prometheus_url()

    for container in containers:
        # Only fetch metrics for active containers or those setting up
        if container.status in [
            STATUS.ACTIVE.value,
            STATUS.SETTING_UP.value,
            STATUS.IDLE.value,
        ]:
            try:
                resource_query_mode, resource_query_targets = (
                    build_resource_query_spec_for_ids_system(container)
                )
                cpu_query = build_resource_metric_query(
                    "container_cpu_usage",
                    match_mode=resource_query_mode,
                    targets=resource_query_targets,
                )
                mem_query = build_resource_metric_query(
                    "container_memory_usage_bytes",
                    match_mode=resource_query_mode,
                    targets=resource_query_targets,
                    convert_to_mb=True,
                )

                async with httpx.AsyncClient() as client:
                    cpu_response = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={"query": cpu_query},
                        timeout=5.0,
                    )

                    mem_response = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={"query": mem_query},
                        timeout=5.0,
                    )

                    cpu_usage = 0.0
                    memory_usage = 0.0

                    if cpu_response.status_code == 200:
                        cpu_data = cpu_response.json()
                        cpu_results = cpu_data.get("data", {}).get("result", [])
                        if cpu_results:
                            cpu_usage = float(cpu_results[0].get("value", [0, 0])[1])

                    if mem_response.status_code == 200:
                        mem_data = mem_response.json()
                        mem_results = mem_data.get("data", {}).get("result", [])
                        if mem_results:
                            memory_usage = float(mem_results[0].get("value", [0, 0])[1])

                    metrics_data.append(
                        {
                            "id": container.id,
                            "name": container.name,
                            "status": container.status,
                            "cpu_usage": round(cpu_usage, 4),
                            "memory_usage": round(memory_usage, 2),
                        }
                    )
            except Exception as e:
                LOGGER.error(f"Error fetching metrics for {container.name}: {e}")
                metrics_data.append(
                    {
                        "id": container.id,
                        "name": container.name,
                        "status": container.status,
                        "cpu_usage": 0,
                        "memory_usage": 0,
                    }
                )

    return JSONResponse(content={"content": metrics_data}, status_code=200)


@router.get("/metrics/historical")
async def get_historical_metrics(
    start: str = Query(
        ..., description="Start time in ISO format or relative (e.g., '1h')"
    ),
    end: str = Query(None, description="End time in ISO format (default: now)"),
    step: str = Query("15s", description="Step interval"),
    expanded_ids: list[int] | None = Query(
        None,
        description="IDS ids whose CIDS components should be returned as individual series.",
    ),
    db=Depends(get_db),
):
    """
    Get historical metrics for all IDS containers within a time range.
    """
    containers = await get_all_container(db, include_deleted=True)
    prometheus_url = _get_prometheus_url()

    # Parse start time (support relative like "1h" or absolute timestamps)
    if start.endswith("m") or start.endswith("h") or start.endswith("d"):
        # Relative time
        start_timestamp = (datetime.now() - parse_relative_time(start)).timestamp()
    else:
        # Absolute time (ISO format)
        start_timestamp = datetime.fromisoformat(
            start.replace("Z", "+00:00")
        ).timestamp()

    # Parse end time (default to now)
    if end and end != "now":
        end_timestamp = datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp()
    else:
        end_timestamp = datetime.now().timestamp()

    expanded_id_set = set(expanded_ids or [])
    container_metrics = {}

    async with httpx.AsyncClient() as client:
        for container in containers:
            if container.status not in [
                STATUS.ACTIVE.value,
                STATUS.SETTING_UP.value,
                STATUS.IDLE.value,
            ]:
                continue

            try:
                resource_query_mode, resource_query_targets = (
                    build_resource_query_spec_for_ids_system(container)
                )
                cpu_query = build_resource_metric_query(
                    "container_cpu_usage",
                    match_mode=resource_query_mode,
                    targets=resource_query_targets,
                )
                mem_query = build_resource_metric_query(
                    "container_memory_usage_bytes",
                    match_mode=resource_query_mode,
                    targets=resource_query_targets,
                    convert_to_mb=True,
                )

                cpu_timestamps, cpu_values = await _query_range_series(
                    client,
                    prometheus_url,
                    cpu_query,
                    start_timestamp,
                    end_timestamp,
                    step,
                )
                mem_timestamps, mem_values = await _query_range_series(
                    client,
                    prometheus_url,
                    mem_query,
                    start_timestamp,
                    end_timestamp,
                    step,
                )

                timestamps = cpu_timestamps or mem_timestamps
                if timestamps:
                    if not cpu_values:
                        cpu_values = [0.0] * len(timestamps)
                    if not mem_values:
                        mem_values = [0.0] * len(timestamps)

                    container_metrics[container.name] = _build_historical_entry(
                        entry_id=container.id,
                        name=container.name,
                        raw_name=container.name,
                        timestamps=timestamps,
                        cpu_values=cpu_values,
                        memory_values=mem_values,
                        entry_type=getattr(container, "type", None),
                        is_component=False,
                    )

                if (
                    getattr(container, "type", None) == "CIDS"
                    and container.id in expanded_id_set
                ):
                    for component in getattr(container, "components", []) or []:
                        component_display_name = (
                            f"{container.name} :: "
                            f"{component.service_name or component.role or component.name}"
                        )
                        component_cpu_query = build_resource_metric_query(
                            "container_cpu_usage",
                            match_mode=RESOURCE_QUERY_MODE_EXACT,
                            targets=[component.name],
                        )
                        component_mem_query = build_resource_metric_query(
                            "container_memory_usage_bytes",
                            match_mode=RESOURCE_QUERY_MODE_EXACT,
                            targets=[component.name],
                            convert_to_mb=True,
                        )

                        component_cpu_timestamps, component_cpu_values = (
                            await _query_range_series(
                                client,
                                prometheus_url,
                                component_cpu_query,
                                start_timestamp,
                                end_timestamp,
                                step,
                            )
                        )
                        component_mem_timestamps, component_mem_values = (
                            await _query_range_series(
                                client,
                                prometheus_url,
                                component_mem_query,
                                start_timestamp,
                                end_timestamp,
                                step,
                            )
                        )

                        component_timestamps = (
                            component_cpu_timestamps or component_mem_timestamps
                        )
                        if not component_timestamps:
                            continue

                        if not component_cpu_values:
                            component_cpu_values = [0.0] * len(component_timestamps)
                        if not component_mem_values:
                            component_mem_values = [0.0] * len(component_timestamps)

                        container_metrics[component_display_name] = (
                            _build_historical_entry(
                                entry_id=component.id,
                                name=component_display_name,
                                raw_name=component.name,
                                timestamps=component_timestamps,
                                cpu_values=component_cpu_values,
                                memory_values=component_mem_values,
                                entry_type="COMPONENT",
                                is_component=True,
                                parent_id=container.id,
                                parent_name=container.name,
                                role=getattr(component, "role", None),
                            )
                        )
            except Exception as e:
                LOGGER.error(
                    f"Error fetching historical metrics for {container.name}: {e}"
                )

    return JSONResponse(content={"content": container_metrics}, status_code=200)


def parse_relative_time(time_str: str) -> timedelta:
    """Parse relative time strings like '1h', '30m', '1d' into timedelta."""
    value = int(time_str[:-1])
    unit = time_str[-1]

    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        return timedelta(hours=1)  # default
