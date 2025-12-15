from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.database import get_db
from app.models.ids_container import get_all_container, IdsContainer
from app.utils import STATUS
from app.logger import LOGGER
import httpx
import os
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/monitoring"
)

@router.get("/metrics")
async def get_monitoring_metrics(db=Depends(get_db)):
    """
    Get real-time metrics for all active IDS containers.
    """
    containers = await get_all_container(db)
    metrics_data = []
    
    # Query Prometheus (not pushgateway) - pushgateway doesn't have query API
    prometheus_url = os.environ.get('PROMETHEUS_URL', 'prometheus:9090')
    if not prometheus_url.startswith('http://') and not prometheus_url.startswith('https://'):
        prometheus_url = f'http://{prometheus_url}'
    
    for container in containers:
        # Only fetch metrics for active containers or those setting up
        if container.status in [STATUS.ACTIVE.value, STATUS.SETTING_UP.value, STATUS.IDLE.value]:
            try:
                async with httpx.AsyncClient() as client:
                    # Query CPU
                    cpu_query = f'container_cpu_usage{{name="{container.name}"}}'
                    cpu_response = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={'query': cpu_query},
                        timeout=5.0
                    )
                    
                    # Query Memory
                    mem_query = f'container_memory_usage_bytes{{name="{container.name}"}} / 1024 / 1024'
                    mem_response = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={'query': mem_query},
                        timeout=5.0
                    )
                    
                    cpu_usage = 0.0
                    memory_usage = 0.0
                    
                    if cpu_response.status_code == 200:
                        cpu_data = cpu_response.json()
                        cpu_results = cpu_data.get('data', {}).get('result', [])
                        if cpu_results:
                            cpu_usage = float(cpu_results[0].get('value', [0, 0])[1])
                    
                    if mem_response.status_code == 200:
                        mem_data = mem_response.json()
                        mem_results = mem_data.get('data', {}).get('result', [])
                        if mem_results:
                            memory_usage = float(mem_results[0].get('value', [0, 0])[1])
                    
                    metrics_data.append({
                        "id": container.id,
                        "name": container.name,
                        "status": container.status,
                        "cpu_usage": round(cpu_usage, 4),
                        "memory_usage": round(memory_usage, 2)
                    })
            except Exception as e:
                LOGGER.error(f"Error fetching metrics for {container.name}: {e}")
                metrics_data.append({
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "cpu_usage": 0,
                    "memory_usage": 0
                })
            
    return JSONResponse(content={"content": metrics_data}, status_code=200)


@router.get("/metrics/historical")
async def get_historical_metrics(
    start: str = Query(..., description="Start time in ISO format or relative (e.g., '1h')"),
    end: str = Query(None, description="End time in ISO format (default: now)"),
    step: str = Query("15s", description="Step interval"),
    db=Depends(get_db)
):
    """
    Get historical metrics for all IDS containers within a time range.
    """
    containers = await get_all_container(db)
    prometheus_url = os.environ.get('PROMETHEUS_URL', 'prometheus:9090')
    if not prometheus_url.startswith('http://') and not prometheus_url.startswith('https://'):
        prometheus_url = f'http://{prometheus_url}'
    
    # Parse start time (support relative like "1h" or absolute timestamps)
    if start.endswith('m') or start.endswith('h') or start.endswith('d'):
        # Relative time
        start_timestamp = (datetime.now() - parse_relative_time(start)).timestamp()
    else:
        # Absolute time (ISO format)
        start_timestamp = datetime.fromisoformat(start.replace('Z', '+00:00')).timestamp()
    
    # Parse end time (default to now)
    if end and end != 'now':
        end_timestamp = datetime.fromisoformat(end.replace('Z', '+00:00')).timestamp()
    else:
        end_timestamp = datetime.now().timestamp()
    
    container_metrics = {}
    
    for container in containers:
        if container.status in [STATUS.ACTIVE.value, STATUS.SETTING_UP.value, STATUS.IDLE.value]:
            try:
                async with httpx.AsyncClient() as client:
                    # Query CPU range
                    cpu_query = f'container_cpu_usage{{name="{container.name}"}}'
                    cpu_response = await client.get(
                        f"{prometheus_url}/api/v1/query_range",
                        params={
                            'query': cpu_query,
                            'start': start_timestamp,
                            'end': end_timestamp,
                            'step': step
                        },
                        timeout=10.0
                    )
                    
                    # Query Memory range
                    mem_query = f'container_memory_usage_bytes{{name="{container.name}"}} / 1024 / 1024'
                    mem_response = await client.get(
                        f"{prometheus_url}/api/v1/query_range",
                        params={
                            'query': mem_query,
                            'start': start_timestamp,
                            'end': end_timestamp,
                            'step': step
                        },
                        timeout=10.0
                    )
                    
                    cpu_values = []
                    mem_values = []
                    timestamps = []
                    
                    if cpu_response.status_code == 200:
                        cpu_data = cpu_response.json()
                        cpu_results = cpu_data.get('data', {}).get('result', [])
                        if cpu_results:
                            values = cpu_results[0].get('values', [])
                            for ts, val in values:
                                if not timestamps or ts not in [t[0] for t in zip(timestamps, cpu_values)]:
                                    timestamps.append(ts)
                                    cpu_values.append(float(val))
                    
                    if mem_response.status_code == 200:
                        mem_data = mem_response.json()
                        mem_results = mem_data.get('data', {}).get('result', [])
                        if mem_results:
                            values = mem_results[0].get('values', [])
                            mem_values = [float(val) for ts, val in values]
                    
                    container_metrics[container.name] = {
                        "id": container.id,
                        "name": container.name,
                        "timestamps": timestamps,
                        "cpu": cpu_values,
                        "memory": mem_values
                    }
            except Exception as e:
                LOGGER.error(f"Error fetching historical metrics for {container.name}: {e}")
    
    return JSONResponse(content={"content": container_metrics}, status_code=200)


def parse_relative_time(time_str: str) -> timedelta:
    """Parse relative time strings like '1h', '30m', '1d' into timedelta."""
    value = int(time_str[:-1])
    unit = time_str[-1]
    
    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    else:
        return timedelta(hours=1)  # default
