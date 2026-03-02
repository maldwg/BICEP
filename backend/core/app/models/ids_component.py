from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class IdsComponent(Base):
    """Represents a component of a CIDS deployment (sensor, aggregator, etc.)"""

    __tablename__ = "ids_component"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(Integer, ForeignKey("ids_system.id"))
    name = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False)  # SENSOR, AGGREGATOR, Other
    host_system_id = Column(Integer, ForeignKey("docker_host_system.id"))
    port = Column(Integer, nullable=True)

    container = relationship("IdsSystem", back_populates="components")
    host_system = relationship("DockerHostSystem", lazy="selectin")

    def get_http_url(self) -> str:
        """Get the HTTP URL for communicating with this component."""
        from app.utils import get_core_host_ip

        if self.host_system:
            host = self.host_system.host
            if "Core" in self.host_system.name or host == "localhost":
                host = get_core_host_ip()
        else:
            host = get_core_host_ip()
        return f"http://{host}:{self.port}"
