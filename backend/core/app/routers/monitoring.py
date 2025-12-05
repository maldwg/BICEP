from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.database import get_db
from app.models.ids_container import get_all_container, IdsContainer
from app.utils import STATUS
from app.prometheus import query_current_cpu_usage, query_current_memory_usage
from app.logger import LOGGER

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
    
    for container in containers:
        # Only fetch metrics for active containers or those setting up
        if container.status in [STATUS.ACTIVE.value, STATUS.SETTING_UP.value, STATUS.IDLE.value]:
            cpu_usage = await query_current_cpu_usage(container.name)
            memory_usage = await query_current_memory_usage(container.name)
            
            metrics_data.append({
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "cpu_usage": cpu_usage if cpu_usage is not None else 0,
                "memory_usage": memory_usage if memory_usage is not None else 0
            })
            
    return JSONResponse(content={"content": metrics_data}, status_code=200)
