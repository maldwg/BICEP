from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from sqlalchemy.orm import relationship, Session

from ..database import Base

class Configuration(Base):
    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True)
    configuration = Column(BLOB, nullable=False)
    description = Column(String(2048))

    containers = relationship("IdsContainer", back_populates="configuration")


def get_config_by_id(db: Session, config_id: int):
    return db.query(Configuration).filter(Configuration.id == config_id).first()
    

def get_all_configurations(db: Session):
    return db.query(Configuration).all()