from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.types import BLOB
from ..bicep_utils.models.ids_base import Alert
from sqlalchemy.orm import relationship, Session
from ..utils import combine_alerts_for_ids_in_alert_dict
from ..database import Base
import sys

class EnsembleTechnique(Base):
    __tablename__ = "ensemble_technique"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(String(2048), nullable=False)
    function_name = Column(String(128), nullable=False)

    ensemble = relationship('Ensemble', back_populates='ensemble_technique')

    async def execute_technique_by_name_on_alerts(self, alerts: list[Alert], ensemble):
        module = sys.modules[__name__]
        func = getattr(module, self.function_name)
        return await func(alerts_dict=alerts, ensemble=ensemble)

def get_all_ensemble_techniques(db: Session):
    return db.query(EnsembleTechnique).all()

def get_ensemble_technique_by_id(db: Session, id: int):
    return db.query(EnsembleTechnique).filter(EnsembleTechnique.id == id).first()

async def majority_vote(alerts_dict: dict, ensemble) -> list[Alert]:
    import json
    # TODO 0: even though only 1 alert is there --> seems like it is getting in the ensemble... why ?
    # TODO 0: make until combine alerts into the discovery unction to have common base
    ids_container_count = len(ensemble.ensemble_ids)
    majority_threshold = ids_container_count / 2
    common_alerts = await combine_alerts_for_ids_in_alert_dict(alerts_dict)
    try:
        print(common_alerts)
    except Exception as e:
        print("could not write common alerts to file")
        print(e)
    majority_voted_alerts = []
    for alert_key, container_dict in common_alerts.items():
        # get ammount of container that have at least 1 alert for the alert key left
        container_voting_for_alert = sum(1 for alerts in container_dict.values() if len(alerts) > 0)
        while container_voting_for_alert > majority_threshold:
            commulative_severity = 0
            # there are potentially multiple alerts for each alert key recognized by the IDS
            # Iterate over each container alerting and combine alerts and avg severity until no majority is voting for the alert
            for _, alerts in container_dict.items():

                alert: Alert = alerts.pop()
                # add alert severity if not none, if none add 0 
                commulative_severity += alert.severity if alert.severity is not None else 0    
            avg_severity = commulative_severity / container_voting_for_alert
            alert.severity = avg_severity
            majority_voted_alerts.append(alert)
            container_voting_for_alert = sum(1 for alerts in container_dict.values() if len(alerts) > 0)
    try:
        print(majority_voted_alerts)
    except Exception as e:
        print("could not write majority votes to file")
        print(e)
    return majority_voted_alerts