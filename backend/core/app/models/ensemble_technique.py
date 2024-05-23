from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from sqlalchemy.orm import relationship, Session

from ..database import Base

class EnsembleTechnique(Base):
    __tablename__ = "ensemble_technique"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    description = Column(String(2048))

    ensemble = relationship('Ensemble', back_populates='ensemble_technique')


def get_all_ensemble_techniques(db: Session):
    return db.query(EnsembleTechnique).all()