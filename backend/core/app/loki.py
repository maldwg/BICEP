import os
import requests
import json
import time
from datetime import datetime, timedelta,timezone
import httpx
from .bicep_utils.models.ids_base import Alert

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
        response = await client.post(f'{LOKI_URL}/loki/api/v1/push',data=data,headers=headers, timeout=300)
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
    print(start_time)
    print(end_time)
    params = {
        'query': query,
        'start': start_time,  
        # reasonable ammount of time delta to have all ids been executed
        'end': end_time,
        'limit': 999999999
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(LOKI_URL+path,params=params, timeout=300)

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
                        print(f"could not parse alert from json {log}")
                        print(20*"-----")
                label = stream["stream"]["container_name"]
                # This check is necessary as the logs are potentially chunked, so the same container can have 2 streams of logs
                # Thus check if there are already logs gathered for a container and then append it or create the key
                if label in alerts:
                    alerts[label].extend(alerts_of_container)
                else:
                    alerts[label] = alerts_of_container
            for container, logs in alerts.items():
                print(f"Found {len(logs)} alerts for {container}")
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

# async def containers_already_pushed_to_loki(containers: list, analysis_id: str) -> bool:
#     container_names = [c.name for c in containers]
#     containers_with_logs = []
#     path = "/loki/api/v1/query_range"

#     query = f'{{ensemble_analysis_id="{analysis_id}"}}'
#     now = datetime.now()
#     t_minus_30_minutes = now - timedelta(minutes=30)
#     timestamp_now = now.isoformat().rsplit(".")[0]+ 'Z'
#     timestamp_t_minus_30_minutes = t_minus_30_minutes.isoformat().rsplit(".")[0]+ 'Z'

#     params = {
#         'query': query,
#         'start': timestamp_t_minus_30_minutes,  
#         # 30 minutes should be enough since old logs are delted 
#         'end': timestamp_now,
#         'limit': 999999999
#     }
#     print(params)
#     async with httpx.AsyncClient() as client:
#         response = await client.get(LOKI_URL+path,params=params, timeout=90)
#     print(response)
#     print(response.content)
#     if response.status_code == 200:
#         try:
#             logs = response.json()
#             for stream in logs["data"]["result"]:
#                 labels = stream["stream"]
#                 print(labels)
#                 container_name = labels["container_name"]
#                 containers_with_logs.append(container_name) 
#             containers_without_logs = list(set(container_names) - set(containers_with_logs))
#             print(container_names)
#             print(containers_with_logs)
#             print(containers_without_logs)
#             if containers_without_logs == []:
#                 # all containers have pushed logs
#                 return True
#             else:
#                 # some container logs are missing
#                 return False
#         except Exception as e:
#             raise(e)
#     else:
#         raise Exception("Could not successfully scrape the API")
    