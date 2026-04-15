from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import METRIC_SERVICE_STATUS


class MetricService(Base):
    __tablename__ = "metric_service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_system_id = Column(
        Integer,
        ForeignKey("docker_host_system.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name = Column(String(255), nullable=False)
    ip = Column(String(255))
    port = Column(Integer)
    status = Column(String(64), nullable=False)
    status_message = Column(String(2048))
    last_registration_at = Column(String(128))

    docker_host_system = relationship(
        "DockerHostSystem", back_populates="metric_service", lazy="selectin"
    )


def serialize_metric_service(metric_service: MetricService | None) -> dict | None:
    if metric_service is None:
        return None

    return {
        "id": metric_service.id,
        "host_system_id": metric_service.host_system_id,
        "name": metric_service.name,
        "ip": metric_service.ip,
        "port": metric_service.port,
        "status": metric_service.status,
        "status_message": metric_service.status_message,
        "last_registration_at": metric_service.last_registration_at,
    }


async def get_metric_service_by_host_id(
    db: AsyncSession, host_id: int
) -> MetricService | None:
    stmt = select(MetricService).where(MetricService.host_system_id == host_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_metric_services(db: AsyncSession) -> list[MetricService]:
    stmt = select(MetricService)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_or_create_metric_service(
    db: AsyncSession,
    host_system_id: int,
    name: str,
    port: int | None = None,
    status: str = METRIC_SERVICE_STATUS.REGISTERING.value,
    status_message: str | None = None,
) -> MetricService:
    metric_service = await get_metric_service_by_host_id(db, host_system_id)
    if metric_service is None:
        metric_service = MetricService(
            host_system_id=host_system_id,
            name=name,
            port=port,
            status=status,
            status_message=status_message,
        )
        db.add(metric_service)
        await db.commit()
        await db.refresh(metric_service)
        return metric_service

    updated = False
    if name and metric_service.name != name:
        metric_service.name = name
        updated = True
    if port is not None and metric_service.port != port:
        metric_service.port = port
        updated = True
    if metric_service.status != status:
        metric_service.status = status
        updated = True
    if status_message is not None and metric_service.status_message != status_message:
        metric_service.status_message = status_message
        updated = True

    if updated:
        await db.commit()
        await db.refresh(metric_service)

    return metric_service


async def update_metric_service(
    db: AsyncSession,
    metric_service: MetricService,
    *,
    name: str | None = None,
    ip: str | None = None,
    port: int | None = None,
    status: str | None = None,
    status_message: str | None = None,
    registered_now: bool = False,
    clear_registration: bool = False,
) -> MetricService:
    if clear_registration:
        metric_service.ip = None
        metric_service.port = None
        metric_service.last_registration_at = None

    if name is not None:
        metric_service.name = name
    if ip is not None:
        metric_service.ip = ip
    if port is not None:
        metric_service.port = port
    if status is not None:
        metric_service.status = status
    if status_message is not None:
        metric_service.status_message = status_message
    if registered_now:
        metric_service.last_registration_at = datetime.utcnow().isoformat()

    await db.commit()
    await db.refresh(metric_service)
    return metric_service
