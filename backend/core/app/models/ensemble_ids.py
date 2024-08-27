from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session

from ..database import Base
from ..utils import ANALYSIS_STATUS

class EnsembleIds(Base):
    __tablename__ = "ensemble_ids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ensemble_id = Column(Integer, ForeignKey("ensemble.id"))
    ids_container_id = Column(Integer, ForeignKey("ids_container.id"))
    status = Column(String(32))

    ensemble = relationship('Ensemble', back_populates='ensemble_ids')
    container = relationship('IdsContainer', back_populates='ensemble_ids')


def get_ensemble_ids_by_ids(ensemble_id: int, container_id: int, db: Session):
    return db.query(EnsembleIds).filter(EnsembleIds.ensemble_id == ensemble_id, EnsembleIds.ids_container_id == container_id).first()

def get_all_ensemble_container(db: Session):
    return db.query(EnsembleIds).all()


async def last_container_sending_logs(container, ensemble, db: Session):
    analysis_status_of_other_containers_in_ensemble: list[EnsembleIds] = db.query(
        EnsembleIds
        ).filter(
            EnsembleIds.ensemble_id == ensemble.id,
            EnsembleIds.ids_container_id != container.id
        ).all()
    for entry in analysis_status_of_other_containers_in_ensemble:
        if entry.status == ANALYSIS_STATUS.PROCESSING.value:
            return False
    return True

async def update_sendig_logs_status(container, ensemble, db: Session, status: ANALYSIS_STATUS):
    entry: EnsembleIds = db.query(EnsembleIds).filter(
        EnsembleIds.ensemble_id == ensemble.id,
        EnsembleIds.ids_container_id == container.id).first()
    entry.status = status
    db.commit()
    db.refresh(entry)