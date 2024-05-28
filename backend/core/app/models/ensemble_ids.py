from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship, Session

from ..database import Base

class EnsembleIds(Base):
    __tablename__ = "ensemble_ids"

    id = Column(Integer, primary_key=True)
    ensemble_id = Column(Integer, ForeignKey("ensemble.id"))
    ids_container_id = Column(Integer, ForeignKey("ids_container.id"))

    ensemble = relationship('Ensemble', back_populates='ensemble_ids')
    container = relationship('IdsContainer', back_populates='ensemble_ids')


def get_ensemble_ids_by_ids(ensemble_id: int, container_id: int, db: Session):
    return db.query(EnsembleIds).filter(EnsembleIds.ensemble_id == ensemble_id, EnsembleIds.ids_container_id == container_id).first()

def get_all_ensemble_container(db: Session):
    return db.query(EnsembleIds).all()