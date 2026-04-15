from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.ids_system import IdsSystem
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
    config_type = Column(String(32), nullable=False, default="CONFIGURATION")

    __mapper_args__ = {
        "polymorphic_identity": "CONFIGURATION",
        "polymorphic_on": config_type,
    }

    container = relationship("IdsSystem", foreign_keys=[IdsSystem.configuration_id])
    containerRuleset = relationship("IdsSystem", foreign_keys=[IdsSystem.ruleset_id])
    # TODO add methods to retrieve configurations content

    async def read_content(self) -> str:
        async with aiofiles.open(self.file_path, mode="r") as f:
            content = await f.read()
            return content


class DeploymentConfig(Configuration):
    __mapper_args__ = {"polymorphic_identity": "DEPLOYMENT"}


class RuntimeConfig(Configuration):
    __mapper_args__ = {"polymorphic_identity": "RUNTIME"}


class RulesetConfig(Configuration):
    __mapper_args__ = {"polymorphic_identity": "RULESET"}


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
        "file_content": base64.b64encode(await configuration.read_content()).decode(
            "utf-8"
        ),  # Encode binary data to Base64, otherwise error when returning pcap files
        "file_type": configuration.file_type,
        "file_path": configuration.file_path,
        "description": configuration.description,
        "config_type": configuration.config_type,
    }
    return serialized_config
