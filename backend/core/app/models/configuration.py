from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from sqlalchemy.orm import relationship, Session
from app.models.ids_container import IdsContainer
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base
import aiofiles
import base64
class Configuration(Base):
    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(32), nullable=False)
    description = Column(String(2048))

    container = relationship("IdsContainer", foreign_keys=[IdsContainer.configuration_id])
    containerRuleset = relationship('IdsContainer', foreign_keys=[IdsContainer.ruleset_id])
# TODO add methods to retrieve configurations content

    async def read_content(self) -> str:
        async with aiofiles.open(self.file_path, mode='r') as f:
            content = await f.read()
            return content

async def get_config_by_id(db: AsyncSession, config_id: int):
    stmt = select(Configuration).where(Configuration.id == config_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() 

async def get_all_configurations(db: AsyncSession):
    stmt = select(Configuration)
    result = await db.execute(stmt)
    return result.scalars().all()  

async def remove_configuration_by_id(db: AsyncSession, config_id: int):
    config = await get_config_by_id(db, config_id)
    if config:
        await db.delete(config)
        await db.commit()

async def add_config(db: AsyncSession, configuration: Configuration):
    db.add(configuration)
    await db.commit() 
    await db.refresh(configuration)  

async def get_all_configurations_by_type(db: AsyncSession, file_type: str):
        stmt = select(Configuration).where(Configuration.file_type == file_type)
        result = await db.execute(stmt)
        return result.scalars().all()
    

async def get_serialized_configuration(configuration):
    serialized_config = {
        "id": configuration.id,
        "name": configuration.name,
        "file_content": base64.b64encode(configuration.read_content).decode('utf-8'),  # Encode binary data to Base64, otherwise error when returning pcap files 
        "file_type": configuration.file_type,
        "file_path": configuration.file_path,
        "description": configuration.description
    }
    return serialized_config