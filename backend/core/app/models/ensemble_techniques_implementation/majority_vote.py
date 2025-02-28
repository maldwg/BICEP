from ...bicep_utils.models.ids_base import Alert
from ...logger import LOGGER
from ...utils import extract_ts_srcip_srcport_dstip_dstport_from_alert

async def majority_vote(alerts_dict: dict, ensemble) -> list[Alert]:
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
        Gets a dict of this shape: {"ids": list[Alert], "ids2": list[Alert], ...}
        returns a dict like : {ts-src_ip-src_port-dst_ip-dst_port: {"ids1": list[Alert], "ids2": list[Alert]}}
    """
    common_alerts = {}
    for container_name, alerts in alerts_dict.items():
        for alert in alerts:
            timestamp, source_ip, source_port, destination_ip, destination_port = extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)
            key = (timestamp, source_ip, source_port, destination_ip, destination_port)
            common_alerts.setdefault(key, {}).setdefault(container_name, []).extend([alert])
    return common_alerts

