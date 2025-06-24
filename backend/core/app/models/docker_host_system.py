from app.database import Base
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship, Session
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import DOCKER_HOST_STATUS
from app.docker import get_docker_client
from app.logger import LOGGER
class DockerHostSystem(Base):
    __tablename__ = "docker_host_system"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    host = Column(String(1024), nullable=False)
    docker_port = Column(Integer)
    status = Column(String(64))

    container = relationship("IdsContainer", back_populates="host_system",lazy="selectin")

    async def check_host_health(self):
        client = get_docker_client(self)
        try:
            version = client.version()
            if version:
                return DOCKER_HOST_STATUS.AVAILABLE.value
        except Exception as e:
            LOGGER.error(e)
            return DOCKER_HOST_STATUS.UNAVAILABLE.value

    async def update_availability(self, db: AsyncSession):
        old_availability = self.status
        new_availability = self.check_host_health()
        if old_availability != new_availability:
            set_host_status(db, self, new_availability)

async def set_host_status(db: AsyncSession, host: DockerHostSystem, status: DOCKER_HOST_STATUS):
    host.status = status
    db.commit()
    db.refresh(host)
    
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
    host_health = await host.check_host_health()
    await db.commit()  
    await db.refresh(host) 

async def remove_host(db: AsyncSession, host_id: int):
    host: DockerHostSystem = await get_host_by_id(db, host_id) 
    if host:  
        await db.delete(host)
        await db.commit()