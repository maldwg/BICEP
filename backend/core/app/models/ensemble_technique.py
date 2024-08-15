from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from sqlalchemy.orm import relationship, Session

from ..database import Base

class EnsembleTechnique(Base):
    __tablename__ = "ensemble_technique"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(String(2048), nullable=False)
    function_name = Column(String(128), nullable=False)

    ensemble = relationship('Ensemble', back_populates='ensemble_technique')


def get_all_ensemble_techniques(db: Session):
    return db.query(EnsembleTechnique).all()

# TODO 10: implement majority vote
def majority_vote():
    pass