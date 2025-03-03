from ..database import Base
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

    container = relationship("IdsContainer", back_populates="host_system",lazy="selectin")


async def get_host_by_id(db: AsyncSession, id: int):
    stmt = select(DockerHostSystem).where(DockerHostSystem.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  

async def get_all_hosts(db: AsyncSession):
    stmt = select(DockerHostSystem)
    result = await db.execute(stmt)
    return result.scalars().all()  

async def add_host_system(db: AsyncSession, host: DockerHostSystem):
    db.add(host)
    await db.commit()  
    await db.refresh(host) 

async def remove_host(db: AsyncSession, host_id: int):
    host: DockerHostSystem = await get_host_by_id(db, host_id) 
    if host:  
        await db.delete(host)
        await db.commit()