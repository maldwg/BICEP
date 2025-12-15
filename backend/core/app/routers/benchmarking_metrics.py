from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from app.database import get_db
from app.prometheus import query_cpu_usage_series, query_memory_usage_series
from app.logger import LOGGER
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
async def get_benchmarking_metrics_series(requests: List[MetricSeriesRequest] = Body(...)):
    """
    Get historical metrics series (CPU, RAM) for a list of benchmarking runs.
    """
    results = {}
    
    for req in requests:
        cpu_series = await query_cpu_usage_series(req.container_name, req.start_time, req.end_time)
        memory_series = await query_memory_usage_series(req.container_name, req.start_time, req.end_time)
        
        results[req.id] = {
            "cpu": cpu_series,
            "memory": memory_series
        }
            
    return JSONResponse(content={"content": results}, status_code=200)
