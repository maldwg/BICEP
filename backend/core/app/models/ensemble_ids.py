from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session

from app.database import Base
from app.utils import ANALYSIS_STATUS
from sqlalchemy.future import select
from app.logger import LOGGER
from sqlalchemy.ext.asyncio import AsyncSession


class EnsembleIds(Base):
    __tablename__ = "ensemble_ids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ensemble_id = Column(Integer, ForeignKey("ensemble.id"))
    ids_container_id = Column(Integer, ForeignKey("ids_container.id"))
    status = Column(String(32))

async def get_ensemble_ids_by_ids(db: AsyncSession, ensemble_id: int, container_id: int):
    stmt = select(EnsembleIds).where(
        EnsembleIds.ensemble_id == ensemble_id,
        EnsembleIds.ids_container_id == container_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  

async def get_all_ensemble_container(db: AsyncSession):
    stmt = select(EnsembleIds)
    result = await db.execute(stmt)
    return result.scalars().all() 

async def last_container_sending_logs(db: AsyncSession ,container, ensemble):
    from datetime import datetime
    stmt = select(EnsembleIds).where(
        EnsembleIds.ensemble_id == ensemble.id,
        EnsembleIds.ids_container_id != container.id
    )
    result = await db.execute(stmt)
    analysis_status_of_other_containers_in_ensemble = result.scalars().all()
    for entry in analysis_status_of_other_containers_in_ensemble:
        # necessary to refresh the entity as otherwise ensembles can work on oudated data and  perceive the status incorrectly
        await db.refresh(entry)
        if entry.status == ANALYSIS_STATUS.PROCESSING.value:
            return False
    return True


async def update_sendig_logs_status(db: AsyncSession, container, ensemble, status: ANALYSIS_STATUS):
    stmt = select(EnsembleIds).where(
        EnsembleIds.ensemble_id == ensemble.id,
        EnsembleIds.ids_container_id == container.id
    )
    result = await db.execute(stmt)
    entry: EnsembleIds = result.scalar_one_or_none()  
    if entry:
        # necessary to refresh the entity as otherwise ensembles can work on oudated data and set the status incorrectly
        await db.refresh(entry)
        entry.status = status
        await db.commit()  
        await db.refresh(entry)  
