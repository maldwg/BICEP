from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from app.database import get_db
from app.models.benchmarking import get_benchmarking_result_by_id
from app.prometheus import (
    deserialize_resource_query_targets,
    query_cpu_usage_series,
    query_memory_usage_series,
)
from pydantic import BaseModel
from typing import List

router = APIRouter(
    prefix="/benchmarking/metrics"
)

class MetricSeriesRequest(BaseModel):
    id: int
    container_name: str
    start_time: str
    end_time: str

@router.post("/series")
async def get_benchmarking_metrics_series(
    requests: List[MetricSeriesRequest] = Body(...), db=Depends(get_db)
):
    """
    Get historical metrics series (CPU, RAM) for a list of benchmarking runs.
    """
    results = {}
    
    for req in requests:
        benchmark_result = await get_benchmarking_result_by_id(db, req.id)

        resource_query_mode = None
        resource_query_targets = None
        if benchmark_result is not None:
            resource_query_mode = benchmark_result.resource_query_mode
            resource_query_targets = deserialize_resource_query_targets(
                benchmark_result.resource_query_targets
            )

        cpu_series = await query_cpu_usage_series(
            req.container_name,
            req.start_time,
            req.end_time,
            match_mode=resource_query_mode,
            targets=resource_query_targets,
        )
        memory_series = await query_memory_usage_series(
            req.container_name,
            req.start_time,
            req.end_time,
            match_mode=resource_query_mode,
            targets=resource_query_targets,
        )
        
        results[req.id] = {
            "cpu": cpu_series,
            "memory": memory_series
        }
            
    return JSONResponse(content={"content": results}, status_code=200)
