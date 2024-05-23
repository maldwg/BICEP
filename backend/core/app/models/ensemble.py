from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session
from .ensemble_ids import EnsembleIds, get_ensemble_ids_by_ids
from ..database import Base

class Ensemble(Base):
    __tablename__ = "ensemble"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    technique_id = Column(Integer, ForeignKey("ensemble_technique.id"))
    status = Column(String(32), nullable=False)
    description = Column(String(2048))

    ensemble_ids = relationship('EnsembleIds', back_populates='ensemble', cascade="all, delete")
    ensemble_technique = relationship('EnsembleTechnique', back_populates='ensemble')


    def add_container(self,container_id: int, db: Session):
        ensemble_ids = EnsembleIds(
            ensemble_id=self.id,
            ids_container_id=container_id
        )
        db.add(ensemble_ids)
        db.commit()
    
    def remove_container(self, container_id: int, db: Session):
        ensemble_ids = get_ensemble_ids_by_ids(self.id, container_id, db)
        db.delete(ensemble_ids)
        db.commit()



def get_all_ids_ensembles(db: Session):
    return db.query(Ensemble).all()

# TODO: make all db actions asynchronous


def get_ensemble_by_id(id: int, db: Session):
    return db.query(Ensemble).filter(Ensemble.id == id).first()

def remove_ensemble(ensemble: Ensemble, db: Session):
    db.delete(ensemble)
    db.commit()

async def add_ensemble(ensemble: Ensemble, db):
    db.add(ensemble)
    db.commit()