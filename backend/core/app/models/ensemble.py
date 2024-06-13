from ..utils import STATUS
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session
from .ensemble_ids import EnsembleIds, get_ensemble_ids_by_ids
from ..database import Base
from ..validation.models import EnsembleUpdate

class Ensemble(Base):
    __tablename__ = "ensemble"

    id = Column(Integer, primary_key=True, autoincrement=True)
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

    def get_enssemble_ids(self, db: Session):
        return db.query(EnsembleIds).filter(EnsembleIds.ensemble_id == self.id).all()

    def get_containers(self, db: Session):
        from .ids_container import IdsContainer
        ensemble_ids = db.query(EnsembleIds).filter(EnsembleIds.ensemble_id == self.id).all()
        id_list = [e_ids.ids_container_id for e_ids in ensemble_ids]
        containers: list[IdsContainer] = db.query(IdsContainer).filter(IdsContainer.id.in_(id_list)).all()
        return containers

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


def update_ensemble(ensemble: EnsembleUpdate, db: Session):
    ensemble_db = db.query(Ensemble).filter(Ensemble.id == ensemble.id).first()
    former_containers = [ensemble_container.ids_container_id for ensemble_container in ensemble_db.get_enssemble_ids(db) ]
    for key, value in ensemble.dict().items():
        setattr(ensemble_db, key, value)
    db.commit()
    db.refresh(ensemble_db)
    new_containers = ensemble.container_ids

    added_containers = list(filter(lambda x: x not in former_containers, new_containers))
    removed_containers = list(filter(lambda x: x not in new_containers, former_containers))

    for container_id in removed_containers:
        ensemble_db.remove_container(container_id, db)
    for container_id in added_containers:
        ensemble_db.add_container(container_id, db)


async def update_ensemble_status(status: STATUS, ensemble: Ensemble, db: Session):
    ensemble.status = status
    db.commit()
    db.refresh(ensemble)


