import os
import requests
import json
import time
from datetime import datetime, timedelta,timezone
import httpx
from .bicep_utils.models.ids_base import Alert
from .logger import LOGGER

LOKI_URL = os.environ.get('LOKI_URL')


async def push_alerts_to_loki(alerts: list[Alert], labels: dict):
    values = [ [str(await get_timestamp_in_nanoseconds()), str(a.to_dict())] for a in alerts]
    log_entry = {
        'streams': [
            {
                'stream': labels,
                'values': values
            }
        ]
    }
    headers = {
        'Content-Type': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        data= json.dumps(log_entry)
        response = await client.post(f'{LOKI_URL}/loki/api/v1/push',data=data,headers=headers, timeout=600)
    return response


async def get_timestamp_in_nanoseconds():
    now = datetime.now(tz=None)
    seconds_since_epoch = now.timestamp()
    nanoseconds_since_epoch = int(seconds_since_epoch * 1_000_000_000)
    nanoseconds_since_epoch += now.microsecond * 1000  
    return nanoseconds_since_epoch

async def get_alerts_from_analysis_id(analysis_id: str):
    from datetime import time

    path = "/loki/api/v1/query_range"

    query = f'{{ensemble_analysis_id="{analysis_id}"}}'
    # Get the current time
    now = datetime.now()

    # Define the 24-hour window (12 hours before and 12 hours after now)
    start_time = (now - timedelta(hours=12)).isoformat() + 'Z'
    end_time = (now + timedelta(hours=12)).isoformat() + 'Z'
    params = {
        'query': query,
        'start': start_time,  
        # reasonable ammount of time delta to have all ids been executed
        'end': end_time,
        'limit': 999999999
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(LOKI_URL+path,params=params, timeout=600)

    if response.status_code == 200:
        try:
            logs = response.json()
            # Do something with the logs
            alerts = {}
            for stream in logs["data"]["result"]:
                alerts_of_container = []
                for _, log in stream["values"]:
                    try:
                        alerts_of_container.append(Alert.from_json(log))
                    except:
                        LOGGER.debug(f"could not parse alert from json {log}")
                label = stream["stream"]["container_name"]
                # This check is necessary as the logs are potentially chunked, so the same container can have 2 streams of logs
                # Thus check if there are already logs gathered for a container and then append it or create the key
                if label in alerts:
                    alerts[label].extend(alerts_of_container)
                else:
                    alerts[label] = alerts_of_container
            for container, logs in alerts.items():
                LOGGER.debug(f"Found {len(logs)} alerts for {container}")
            return alerts
        except Exception as e:
            raise(e)
    else:
        LOGGER.error(f"Failed to retrieve logs: {response.status_code}")


async def clean_up_alerts_in_loki(analysis_id: str):
    """
    This method is designed to mark logs in loki to be deleted. Attention!: This does not work reliably.
    The logs are deleted but after an uncertain ammount of time (between 20 seconds and 5 minutes). Do not rely on this for timebased actions
    """
    # search for logs with the analysis id, that are from a single container, if container == None, then the logs are aggregated logs, which should not be deleted
    query = f'{{ensemble_analysis_id="{analysis_id}",container_name!="None"}}'
    path = "/loki/api/v1/delete"
    now = datetime.now()
    # Query parameters
    params = {
        'query': query,
        'start': int(datetime.timestamp(now - timedelta(minutes=10))),  # Replace with actual start time
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(LOKI_URL+path,params=params, timeout=600)
    return response