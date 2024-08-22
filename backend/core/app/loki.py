import os
import requests
import json
import time
import httpx

from .bicep_utils.models.ids_base import Alert

LOKI_URL = os.environ.get('LOKI_URL')


async def push_alerts_to_loki(alerts: list[Alert], labels: dict):
    values = [ [str(time.time_ns()), str(a.to_dict())] for a in alerts]
    log_entry = {
        "streams": [
            {
                "stream": labels,
                "values": values
            }
        ]
    }
    headers = {
        'Content-Type': 'application/json'
    }
    # set timeout to 90 seconds to be able to send all logs

    async with httpx.AsyncClient() as client:
        data= json.dumps(log_entry)
        response = await client.post(f'{LOKI_URL}/loki/api/v1/push',data=data,headers=headers, timeout=90)
    return response


async def get_alerts_from_analysis_id(analysis_id: str):
    from datetime import datetime, time, timedelta

    path = "/loki/api/v1/query_range"

    query = f"{{ensemble_analysis_id={analysis_id}}}"
    now = datetime.now()

    params = {
        'query': query,
        'start': now,  
        # reasonable ammount of time delta to have all ids been executed
        'end': now - timedelta(hours=12),
        'limit': 1000000
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(LOKI_URL+path,params=params, timeout=90)

    if response.status_code == 200:
        try:
            logs = response.json()
            # Do something with the logs
            alerts = []
            for stream in logs["data"]["result"]:
                alerts.append([log for _, log in stream["values"]])
            return alerts
        except Exception as e:
            raise(e)
    else:
        print(f"Failed to retrieve logs: {response.status_code}")


async def clean_up_alerts_in_loki(analysis_id: str):
    pass


async def containers_already_pushed_to_loki(containers: list):
    pass