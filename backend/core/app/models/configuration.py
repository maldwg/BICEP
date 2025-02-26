from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from sqlalchemy.orm import relationship, Session
from .ids_container import IdsContainer
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import Base

class Configuration(Base):
    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    configuration = Column(BLOB, nullable=False)
    file_type = Column(String(32), nullable=False)
    description = Column(String(2048))

    container = relationship("IdsContainer", back_populates="configuration", foreign_keys=[IdsContainer.configuration_id])
    containerRuleset = relationship('IdsContainer', back_populates='ruleset', foreign_keys=[IdsContainer.ruleset_id])

async def get_config_by_id(db: AsyncSession, config_id: int):
    stmt = select(Configuration).where(Configuration.id == config_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  # Return a single row or None

async def get_all_configurations(db: AsyncSession):
    stmt = select(Configuration)
    result = await db.execute(stmt)
    return result.scalars().all()  # Return all results

async def remove_configuration_by_id(db: AsyncSession, config_id: int):
    config = await get_config_by_id(db, config_id)
    if config:
        await db.delete(config)
        await db.commit()

async def add_config(db: AsyncSession, configuration: Configuration):
    db.add(configuration)
    await db.commit()  # Commit asynchronously
    await db.refresh(configuration)  # Refresh to get updated values

async def get_all_configurations_by_type(db: AsyncSession, file_type: str):
        stmt = select(Configuration).where(Configuration.file_type == file_type)
        result = await db.execute(stmt)
        return result.scalars().all()