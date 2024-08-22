from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from ..bicep_utils.models.ids_base import Alert
from sqlalchemy.orm import relationship, Session

from ..database import Base

class EnsembleTechnique(Base):
    __tablename__ = "ensemble_technique"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(String(2048), nullable=False)
    function_name = Column(String(128), nullable=False)

    ensemble = relationship('Ensemble', back_populates='ensemble_technique')

    async def execute_technique_by_name_on_alerts(self, alerts: list[Alert]):
        func = getattr(__name__, self.function_name)
        return func(alerts)

def get_all_ensemble_techniques(db: Session):
    return db.query(EnsembleTechnique).all()

async def get_ensemble_technique_by_id(db: Session, id: int):
    return db.query(EnsembleTechnique).filter(EnsembleTechnique.id == id).first()

# TODO 10: implement majority vote
async def majority_vote(alerts: list[Alert]):
    return alerts


