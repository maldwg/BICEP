from pydantic import BaseModel


class MetricPushRequest(BaseModel):
    """Schema for metrics pushed from IDS containers"""

    container_id: int
    container_name: str
    cpu_usage: float
    memory_usage: float
