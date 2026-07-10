import logging
import os
import json
from datetime import datetime, timedelta
import httpx
from app.bicep_utils.models.ids_base import Alert
import asyncio
from fastapi.responses import JSONResponse

logger = logging.getLogger('bicep.loki')

LOKI_URL = os.environ.get('LOKI_URL')

async def push_alerts_to_loki(alerts: list[Alert], labels: dict):
    responses = []
    values = await asyncio.to_thread(combine_timestamps_and_alerts, alerts)
    chunked_values = await get_chunk_of_values(values)
    logger.debug(f"Partitioned the values for loki into {len(chunked_values)} chunks")
    for chunk in chunked_values:          
        log_entry = {
            'streams': [
                {
                    'stream': labels,
                    'values': chunk
                }
            ]
        }
        response = await send_alerts_in_chunk(log_entry)
        responses.append(response)
    for response in responses:
        if response.status_code not in [200, 204]:
            logger.debug(f"Did not sucessfully push all alerts to loki, got statuscode {response.status_code}")
            return JSONResponse(content={"message": f"Did not succesfully send data to loki in {len(responses)} chunks"}, status_code=500)
    logger.debug(f"Succesfully pushed alerts to loki")
    return JSONResponse(content={"message": f"succesfully send data to loki in {len(responses)} chunks"}, status_code=200)

# chunksize of 50000 ~15MB per chunk
async def get_chunk_of_values(values,alert_chunk_size = 50000):
    chunked_values = []
    length_of_values = len(values)
    parts_to_split_in = (length_of_values + alert_chunk_size )// alert_chunk_size
    for i in range(0, parts_to_split_in):
        start_idx = i * alert_chunk_size
        end_idx = start_idx + alert_chunk_size
        if end_idx <= length_of_values:
            chunked_values.append(values[start_idx:end_idx])
        else:
            chunked_values.append(values[start_idx:])
    return chunked_values

async def send_alerts_in_chunk(chunk_log_entry):
    headers = {
        'Content-Type': 'application/json'
    }
    async with httpx.AsyncClient() as client:
        data= json.dumps(chunk_log_entry)
        response = await client.post(f'{LOKI_URL}/loki/api/v1/push',data=data,headers=headers, timeout=600)
    return response

def combine_timestamps_and_alerts(alerts):
    return  [ [str(get_timestamp_in_nanoseconds()), str(a.to_dict())] for a in alerts]


def get_timestamp_in_nanoseconds():
    now = datetime.now(tz=None)
    seconds_since_epoch = now.timestamp()
    nanoseconds_since_epoch = int(seconds_since_epoch * 1_000_000_000)
    nanoseconds_since_epoch += now.microsecond * 1000  
    return nanoseconds_since_epoch

async def get_all_alerts_for_ensemble_from_analysis_id(analysis_id: str):

    path = "/loki/api/v1/query_range"
    query = f'{{ensemble_analysis_id="{analysis_id}"}}'
    now = datetime.now()

    # Define the total time range (24 hours: 12 before and 12 after now)
    full_start_time = now - timedelta(hours=12)
    full_end_time = now + timedelta(hours=12)

    alerts = {}

    async with httpx.AsyncClient() as client:
            params = {
                'query': query,
                'start': full_start_time.isoformat() + 'Z',
                'end': full_end_time.isoformat() + 'Z',
                'limit': 999999999 
            }

            response = await client.get(LOKI_URL + path, params=params, timeout=120)

            if response.status_code == 200:
                try:
                    logs = response.json()
                    for stream in logs["data"]["result"]:
                        alerts_of_container = []
                        for _, log in stream["values"]:
                            try:
                                alerts_of_container.append(Alert.from_json(log))
                            except:
                                logger.debug(f"Could not parse alert from JSON: {log}")

                        label = stream["stream"]["container_name"]
                        if label in alerts:
                            alerts[label].extend(alerts_of_container)
                        else:
                            alerts[label] = alerts_of_container

                except Exception as e:
                    logger.error(f"Error processing logs: {e}")
                    raise

            else:
                logger.error(f"Failed to retrieve logs: {response.status_code}")

    for container, logs in alerts.items():
        logger.debug(f"Found {len(logs)} alerts for {container}")

    return alerts


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