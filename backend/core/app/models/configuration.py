from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from sqlalchemy.orm import relationship, Session
from .ids_container import IdsContainer

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

def get_config_by_id(db: Session, config_id: int):
    return db.query(Configuration).filter(Configuration.id == config_id).first()
    

def get_all_configurations(db: Session):
    return db.query(Configuration).all()

def remove_configuration_by_id(db, id):
    config = get_config_by_id(db, id)
    db.delete(config)
    db.commit()

def add_config(db: Session, configuration: Configuration):
    db.add(configuration)
    db.commit()


def get_all_configurations_by_type(db: Session, file_type: str):
    return db.query(Configuration).filter(Configuration.file_type == file_type).all()