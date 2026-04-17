from app.bicep_utils.models.ids_base import Alert
from app.logger import LOGGER
from app.utils import extract_ts_srcip_srcport_dstip_dstport_from_alert

async def majority_vote(alerts_dict: dict, ensemble) -> list[Alert]:
    """
    Method to calculate which alerts of an ensemble are majority voted ones

    Args:
        alerts_dict (dict): Dict that holds for each IDS in the ensemble a list of alerts
        ensemble: (Ensemble): Ensemble Object according to the ORM

    Returns:
        majority_voted_alerts (list[Alert]): List of alerts the ensemble voted for 
    """
    common_alerts = await combine_alerts_for_ids_in_alert_dict(alerts_dict)
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


async def combine_alerts_for_ids_in_alert_dict(alerts_dict: dict) -> dict:
    """
    Transforms a dictionary that holds alerts for each IDS in the ensemble into a structured format.

    The returned dictionary maps a key composed of `timestamp`, `source_ip`, `source_port`,
    `destination_ip`, and `destination_port` to another dictionary. This inner dictionary
    contains IDS names as keys and lists of `Alert` objects as values.

    Args:
        alerts_dict (dict): A dictionary where each key is an IDS name and the
            value is a list of `Alert` objects.

    Returns:
        dict: A dictionary grouping alerts by their common attributes. Each key
        is a tuple containing `(timestamp, source_ip, source_port,
        destination_ip, destination_port)`, and each value maps IDS names to
        lists of matching alerts.
    """
    common_alerts = {}
    for container_name, alerts in alerts_dict.items():
        for alert in alerts:
            timestamp, source_ip, source_port, destination_ip, destination_port = extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)
            key = (timestamp, source_ip, source_port, destination_ip, destination_port)
            common_alerts.setdefault(key, {}).setdefault(container_name, []).extend([alert])
    return common_alerts
