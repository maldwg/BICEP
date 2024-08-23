from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from ..bicep_utils.models.ids_base import Alert
from sqlalchemy.orm import relationship, Session
from ..utils import combine_alerts_for_ids_in_alert_dict
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

async def majority_vote(alerts_dict: dict) -> list[Alert]:
    ids_container_count = len(alerts_dict)
    majority_threshold = ids_container_count / 2
    common_alerts = await combine_alerts_for_ids_in_alert_dict(alerts_dict)
    majority_voted_alerts = []
    for alert_key, container_dict in common_alerts.items():
        container_voting_for_alert = len(container_dict)
        while container_voting_for_alert > majority_threshold:
            commulative_severity = 0
            # there are potentially multiple alerts for each alert key recognized by the IDS
            # Iterate over each container alerting and combine alerts and avg severity until no majority is voting for the alert
            for container_name, alerts in container_dict.items():
                # remove one entry for every container and keep only one for reference
                alert: Alert = alerts.pop()
                # remove containers with empty lists, so they are not voting anymore
                if len(alerts) == 0:
                    container_dict.pop(container_name)
                commulative_severity += alert.severity
            avg_severity = commulative_severity / container_voting_for_alert
            alert.severity = avg_severity
            majority_voted_alerts.append([alert])
            container_voting_for_alert = len(container_dict)
    return majority_voted_alerts