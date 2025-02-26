from ..database import Base, get_db_session_context
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship, Session
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
class DockerHostSystem(Base):
    __tablename__ = "docker_host_system"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    host = Column(String(1024), nullable=False)
    docker_port = Column(Integer)

    container = relationship("IdsContainer", back_populates="host_system", lazy="selectin")


async def get_host_by_id(db: AsyncSession, id: int):
    stmt = select(DockerHostSystem).where(DockerHostSystem.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  # Return a single result or None

async def get_all_hosts(db: AsyncSession):
    stmt = select(DockerHostSystem)
    result = await db.execute(stmt)
    return result.scalars().all()  # Return all results

async def add_host_system(db: AsyncSession, host: DockerHostSystem):
    db.add(host)
    await db.commit()  # Commit asynchronously
    await db.refresh(host)  # Refresh after commit

async def remove_host(db: AsyncSession, host_id: int):
    host: DockerHostSystem = await get_host_by_id(host_id)  # Await the result
    if host:  # Ensure the host exists before attempting to delete
        await db.delete(host)
        await db.commit()  # Commit asynchronously