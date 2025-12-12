from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.logger import LOGGER
import httpx
import os
from app.models.metrics import MetricPushRequest

router = APIRouter(
    prefix="/metrics"
)

@router.post("/push")
async def receive_metrics(metrics: MetricPushRequest):
    """
    Receive metrics from IDS containers and forward to Prometheus pushgateway.
    
    Args:
        metrics: Container metrics (CPU in cores, Memory in MB)
        
    Returns:
        Success/failure response
    """
    try:
        # Get Prometheus pushgateway URL
        prometheus_pushgateway = os.environ.get('PROMETHEUS_PUSH_GATEWAY_URL', 'prometheus-push-gateway:9091')
        if not prometheus_pushgateway.startswith('http://') and not prometheus_pushgateway.startswith('https://'):
            prometheus_pushgateway = f'http://{prometheus_pushgateway}'
        
        # Create Prometheus metrics format
        # Use container_name as job label for compatibility with existing queries
        job_name = f"ids_container_{metrics.container_id}"
        
        # Format metrics in Prometheus exposition format
        metrics_data = f"""# TYPE container_cpu_usage gauge
# HELP container_cpu_usage CPU usage in cores
container_cpu_usage{{container_id="{metrics.container_id}",name="{metrics.container_name}"}} {metrics.cpu_usage}
# TYPE container_memory_usage_bytes gauge
# HELP container_memory_usage_bytes Memory usage in bytes
container_memory_usage_bytes{{container_id="{metrics.container_id}",name="{metrics.container_name}"}} {metrics.memory_usage * 1024 * 1024}
"""
        
        # Push to Prometheus pushgateway
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{prometheus_pushgateway}/metrics/job/{job_name}",
                content=metrics_data,
                headers={"Content-Type": "text/plain"},
                timeout=5.0
            )
            
            if response.status_code in [200, 202]:
                LOGGER.debug(f"Successfully pushed metrics for container {metrics.container_id}")
                return JSONResponse({"status": "success"}, status_code=200)
            else:
                LOGGER.warning(f"Failed to push to Prometheus: {response.status_code}")
                return JSONResponse({"status": "failed", "error": "Prometheus push failed"}, status_code=500)
                
    except Exception as e:
        LOGGER.error(f"Error receiving/forwarding metrics: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
