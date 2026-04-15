from pydantic import BaseModel


class MetricServiceRegistrationRequest(BaseModel):
    """Schema used by the host metric service to register itself."""

    ip: str
    name: str
    port: int
