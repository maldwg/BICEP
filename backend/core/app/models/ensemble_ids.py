from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session

from ..database import Base, get_db_session_context
from ..utils import ANALYSIS_STATUS
from sqlalchemy.future import select
from ..logger import LOGGER
from sqlalchemy.ext.asyncio import AsyncSession


class EnsembleIds(Base):
    __tablename__ = "ensemble_ids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ensemble_id = Column(Integer, ForeignKey("ensemble.id"))
    ids_container_id = Column(Integer, ForeignKey("ids_container.id"))
    status = Column(String(32))

    ensemble = relationship('Ensemble', back_populates='ensemble_ids', lazy="selectin")
    container = relationship('IdsContainer', back_populates='ensemble_ids', lazy="selectin")

# EnsembleIds-related functions
async def get_ensemble_ids_by_ids(db: AsyncSession, ensemble_id: int, container_id: int):
    stmt = select(EnsembleIds).where(
        EnsembleIds.ensemble_id == ensemble_id,
        EnsembleIds.ids_container_id == container_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  # Return a single result or None

async def get_all_ensemble_container(db: AsyncSession):
    stmt = select(EnsembleIds)
    result = await db.execute(stmt)
    return result.scalars().all()  # Return all results

async def last_container_sending_logs(db: AsyncSession ,container, ensemble):
    stmt = select(EnsembleIds).where(
        EnsembleIds.ensemble_id == ensemble.id,
        EnsembleIds.ids_container_id != container.id
    )
    result = await db.execute(stmt)
    analysis_status_of_other_containers_in_ensemble = result.scalars().all()
    for entry in analysis_status_of_other_containers_in_ensemble:
        LOGGER.debug(f"analysis status: {entry.ids_container_id} - {entry.status}")
        if entry.status == ANALYSIS_STATUS.PROCESSING.value:
            LOGGER.debug("Not the last container, there are others that are ")
            return False
    LOGGER.debug("Last container as all are having the status LOGS_SENT")
    return True

async def update_sendig_logs_status(db: AsyncSession, container, ensemble, status: ANALYSIS_STATUS):
    LOGGER.debug(f"Updating sending logs status for {container.name} to status {status}")
    stmt = select(EnsembleIds).where(
        EnsembleIds.ensemble_id == ensemble.id,
        EnsembleIds.ids_container_id == container.id
    )
    result = await db.execute(stmt)
    entry: EnsembleIds = result.scalar_one_or_none()  # Await the result
    if entry:
        entry.status = status
        await db.commit()  # Commit asynchronously
        await db.refresh(entry)  # Refresh asynchronously
        db.expire_all()