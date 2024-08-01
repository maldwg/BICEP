import os
import requests
import json
import time
from datetime import datetime
from .bicep_utils.models.ids_base import Alert

LOKI_URL = os.environ.get('LOKI_URL')

async def push_alerts_to_loki(alerts: list[Alert], labels: dict):
    # TODO 9: Works propably fine bnut since suricata timesampt is 2018 lok rejects --> hwo to configure loki correctly or use which timestamp ???
    values = [ [await timestamp_in_nano_seconds(), str(a.to_dict())] for a in alerts]
    print(values)
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
    response = requests.post(f'{LOKI_URL}/loki/api/v1/push', headers=headers, data=json.dumps(log_entry))
    print(log_entry)
    return response


async def timestamp_in_nano_seconds():
    timestamp = datetime.now().isoformat()
    parsed_time = datetime.fromisoformat(timestamp)
    epoch = datetime(1970, 1, 1, tzinfo=None)
    seconds_since_epoch = (parsed_time - epoch).total_seconds()
    nanoseconds_since_epoch = str(int(seconds_since_epoch * 1e9))
    return nanoseconds_since_epoch