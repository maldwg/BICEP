from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession


class IdsTool(Base):
    __tablename__ = "ids_tool"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    ids_type = Column(String(64), nullable=False)
    analysis_method = Column(String(64), nullable=False)
    requires_ruleset = Column(Boolean, nullable=False)
    image_name = Column(String(128), nullable=False)
    image_tag = Column(String(64), nullable=False)
    deployment_type = Column(String(64), nullable=False, default="SINGLE_CONTAINER")
    required_env_vars = Column(String(512), nullable=True, default="")

    container = relationship("IdsSystem", lazy="selectin")


async def get_ids_by_id(db: AsyncSession, ids_id: int):
    stmt = select(IdsTool).where(IdsTool.id == ids_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_tools(db: AsyncSession):
    stmt = select(IdsTool)
    result = await db.execute(stmt)
    return result.scalars().all()


async def add_ids_tool(db: AsyncSession, tool: "IdsTool"):
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return tool


async def update_ids_tool(db: AsyncSession, tool_update):
    stmt = select(IdsTool).where(IdsTool.id == tool_update.id)
    result = await db.execute(stmt)
    tool_db = result.scalar_one_or_none()
    if not tool_db:
        return None
    for key, value in tool_update.model_dump(exclude={"id"}).items():
        setattr(tool_db, key, value)
    await db.commit()
    await db.refresh(tool_db)
    return tool_db


async def delete_ids_tool(db: AsyncSession, tool_id: int):
    stmt = select(IdsTool).where(IdsTool.id == tool_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()
    if tool:
        await db.delete(tool)
        await db.commit()
    return tool
