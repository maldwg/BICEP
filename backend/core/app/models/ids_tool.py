from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Session
from ..database import Base
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

    container = relationship("IdsContainer", lazy="selectin")


async def get_ids_by_id(db: AsyncSession, ids_id: int):
    stmt = select(IdsTool).where(IdsTool.id == ids_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_all_tools(db: AsyncSession):
    stmt = select(IdsTool)
    result = await db.execute(stmt)
    return result.scalars().all()