import os
import requests
import json
import time
import httpx
from datetime import datetime, timedelta
from .bicep_utils.models.ids_base import Alert

LOKI_URL = os.environ.get('LOKI_URL')


async def push_alerts_to_loki(alerts: list[Alert], labels: dict):
    values = [ [str(time.time_ns()), str(a.to_dict())] for a in alerts]
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


    # set timeout to 90 seconds to be able to send all logs

    async with httpx.AsyncClient() as client:
        data= json.dumps(log_entry)
        print(data)
        print(50*"----")
        response = await client.post(f'{LOKI_URL}/loki/api/v1/push',data=data,headers=headers, timeout=90)
        print(response)
        print(response.content)
    return response


async def get_alerts_from_analysis_id(analysis_id: str):
    from datetime import datetime, time, timedelta

    path = "/loki/api/v1/query_range"

    query = f"{{ensemble_analysis_id={analysis_id}}}"
    now = time.time_ns()
    t_minus_12_hours = now - (12 * 60 * 60 * int(1e9))
    params = {
        'query': query,
        'start': t_minus_12_hours,  
        # reasonable ammount of time delta to have all ids been executed
        'end': now,
        'limit': 1000000
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(LOKI_URL+path,params=params, timeout=90)

    print(response)
    print(response.content)
    if response.status_code == 200:
        try:
            logs = response.json()
            # Do something with the logs
            alerts = {}
            for stream in logs["data"]["result"]:
                alerts_of_container=([log for _, log in stream["values"]])
                label = stream["stream"]["container_name"]
                alerts[label] = alerts_of_container
            return alerts
        except Exception as e:
            raise(e)
    else:
        print(f"Failed to retrieve logs: {response.status_code}")


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
        response = await client.post(LOKI_URL+path,params=params, timeout=90)
    return response

async def containers_already_pushed_to_loki(containers: list, analysis_id: str) -> bool:
    container_names = [c.name for c in containers]
    path = "/loki/api/v1/query_range"

    query = f"{{ensemble_analysis_id={analysis_id}}}"
    now = datetime.now()

    params = {
        'query': query,
        'start': now,  
        # 30 minutes should be enough since old logs are delted 
        'end': now - timedelta(minutes=30),
        'limit': 1000000
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(LOKI_URL+path,params=params, timeout=90)
    
    if response.status_code == 200:
        try:
            logs = response.json()
            # Do something with the logs
            containers_with_logs = [ labels["container_name"] for labels in logs["data"]["result"]["stream"]]
            containers_without_logs = list(set(container_names) - set(containers_with_logs))
            if containers_with_logs == []:
                return True
            else:
                return False
        except Exception as e:
            raise(e)
    else:
        raise Exception("Could not successfully scrape the API")
    