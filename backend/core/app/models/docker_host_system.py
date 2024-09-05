from ..database import Base
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship, Session

class DockerHostSystem(Base):
    __tablename__ = "docker_host_system"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    host = Column(String(1024), nullable=False)
    docker_port = Column(Integer)

    container = relationship("IdsContainer", back_populates="host_system")

def get_host_by_id(id: int, db: Session):
    return db.query(DockerHostSystem).filter(DockerHostSystem.id == id).first()

def get_all_hosts(db: Session):
    return db.query(DockerHostSystem).all()


def add_host_system(host: DockerHostSystem ,db:Session):
    db.add(host)
    db.commit()
    db.refresh(host)

def remove_host(host_id: int ,db:Session):
    host: DockerHostSystem = get_host_by_id(host_id, db)
    db.delete(host)
    db.commit()