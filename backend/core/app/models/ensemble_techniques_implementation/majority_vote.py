from ...bicep_utils.models.ids_base import Alert
from ...logger import LOGGER

async def majority_vote(common_alerts: dict, ensemble) -> list[Alert]:
    ids_container_count = len(ensemble.ensemble_ids)
    majority_threshold = ids_container_count / 2
    majority_voted_alerts = []
    for alert_key, container_dict in common_alerts.items():
        # get ammount of container that have at least 1 alert for the alert key left
        container_voting_for_alert = sum(1 for alerts in container_dict.values() if len(alerts) > 0)
        while container_voting_for_alert > majority_threshold:
            cummulative_severity = 0
            # there are potentially multiple alerts for each alert key recognized by the IDS
            # Iterate over each container alerting and combine alerts and avg severity until no majority is voting for the alert
            for container_name, alerts in container_dict.items():
                alert: Alert = alerts.pop()
                # add alert severity if not none, if none add 0 
                cummulative_severity += alert.severity if alert.severity is not None else 0    
            avg_severity = cummulative_severity / container_voting_for_alert
            alert.severity = avg_severity
            majority_voted_alerts.append(alert)
            container_voting_for_alert = sum(1 for alerts in container_dict.values() if len(alerts) > 0)
    LOGGER.debug(f"length of total majority voted alerts is {len(majority_voted_alerts)}")
    return majority_voted_alerts

