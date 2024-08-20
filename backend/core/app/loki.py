import os
import requests
import json
import time
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
    response = requests.post(f'{LOKI_URL}/loki/api/v1/push', headers=headers, data=json.dumps(log_entry), timeout=90)
    print(response)
    return response

