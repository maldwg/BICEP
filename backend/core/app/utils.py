import asyncio
import base64
import aiofiles
from http.client import HTTPResponse
import io
import socket
from contextlib import closing
from enum import Enum
import os
import httpx
from fastapi import Response, Request
import pandas as pd
import csv 
from app.prometheus import push_evaluation_metrics_to_prometheus
from app.models.dataset import Dataset
from app.bicep_utils.models.ids_base import Alert
from dateutil import parser
import uuid
import shutil
from fastapi.responses import JSONResponse
from app.logger import LOGGER

def get_stream_metric_tasks(request: Request):
    return request.app.state.stream_metric_tasks

dataset_addition_tasks = set()

class STATUS(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    SETTING_UP = "setting-up"


class ANALYSIS_STATUS(Enum):
    LOGS_SENT = "LOGS_SENT"
    PROCESSING = "PROCESSING"
    IDLE = "IDLE"

class FILE_TYPES(Enum):
    CONFIG = "configuration"
    TEST_DATA = "test-data"
    RULE_SET = "rule-set"


def file_type_is_accepted(file_type: str, file_ending: str):
    match file_type:
        case FILE_TYPES.CONFIG.value:
            return True if file_ending in ["lua", "yaml", "xml", "conf"] else False
        case FILE_TYPES.TEST_DATA.value:
            return True if file_ending in ["pcap", "csv"] else False
        case FILE_TYPES.RULE_SET.value:
            return True if file_ending in ["rules"] else False
    return False
def find_free_port():
    # TODO 10: Adapt this to also find free ports on remote hosts --> could be hard 
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
    

def get_core_host():
    return os.popen("/sbin/ip route|awk '/default/ { print $3 }'").read().strip()
   

def get_serialized_confgigurations(configurations):
    serialized_configs = []
    for config in configurations:
        serialized_config = {
            "id": config.id,
            "name": config.name,
            "configuration": base64.b64encode(config.configuration).decode('utf-8'),  # Encode binary data to Base64, otherwise error when returning pcap files 
            "file_type": config.file_type,
            "description": config.description
        }
        serialized_configs.append(serialized_config)
    return serialized_configs

async def deregister_container_from_ensemble(container):
    container_url = container.get_container_http_url()
    endpoint = f"/configure/ensemble/remove"
    async with httpx.AsyncClient() as client:
            response: HTTPResponse = await client.post(container_url+endpoint)

    return response

def create_response_message(message: str, status_code: int):
    return Response(content=f"{{ \"message\": \"{message}\" }}", status_code=status_code)

def create_response_error(message: str, status_code: int):
    return Response(content=f"{{ \"error\": \"{message}\" }}", status_code=status_code)

def create_generic_response_message_for_ensemble(message: str, status_code: int):
    return {"content": message, "status_code": status_code}

async def start_static_analysis(container, form_data, dataset):
    endpoint = "/analysis/static"
    container_url = container.get_container_http_url()
    async def send_request_in_background(): 
        try:
            async with httpx.AsyncClient() as client:  
                with open(dataset.data_file_path, "rb") as f:
                    form_data["dataset"] = (dataset.name, f, "application/octet-stream")
                    # set timeout to 600 seconds, as uploads can take a while
                    response = await client.post(container_url+endpoint,files=form_data, timeout=180)    
                    response.raise_for_status()
        except Exception as e:
            LOGGER.error(e)
    task = asyncio.create_task(send_request_in_background())
    return JSONResponse(content={"message": "Successfully sending data in the background"}, status_code=200)

async def start_network_analysis(container, data):
    endpoint = "/analysis/network"
    container_url = container.get_container_http_url()
    async with httpx.AsyncClient() as client:
        response = await client.post(container_url+endpoint, data=data)
    return response

async def stop_analysis(container):
    container_url = container.get_container_http_url()
    endpoint = "/analysis/stop"
    async with httpx.AsyncClient() as client:
        response: HTTPResponse = await client.post(container_url+endpoint)
    return response

async def parse_response_for_triggered_analysis(response: HTTPResponse, container, analysis_type: str, ensemble_id: int = None):
    if response.status_code == 200:
        message = f"container {container.id} - {analysis_type} analysis triggered"
        if ensemble_id != None:
            message = f"container {container.id} - {analysis_type} analysis for ensemble {ensemble_id} triggered"
        parsed_response = create_response_message(message, 200)
    else:
        message = f"container {container.id} - {analysis_type} analysis could not be triggered"
        if ensemble_id != None:
            message = f"container {container.id} - {analysis_type} analysis for ensemble {ensemble_id} could not be triggered"
        parsed_response = create_response_error(message, 500)
    return parsed_response


async def calculate_and_add_dataset(data_file, data_file_ending, labels_file, labels_file_ending, name, description, dataset_type, db):
    from .models.dataset import Dataset, add_dataset
    byte_stream = io.BytesIO(labels_file)
    text_stream = io.TextIOWrapper(byte_stream, encoding='utf-8')
    
    benign, malicious = await dataset_type.get_benign_and_malicious_counts(text_stream)

    uid = str(uuid.uuid4())
    base_path = os.getenv("DATASET_BASE_PATH")
    dataset_storage_location = f"{base_path}/{name}/{uid}" 
    
    data_file_path = f"{dataset_storage_location}/dataset.{data_file_ending}"
    labels_file_path = f"{dataset_storage_location}/dataset.{labels_file_ending}"

    await create_directory(dataset_storage_location)
    await save_file_to_disk(data_file, data_file_path)
    await save_file_to_disk(labels_file, labels_file_path)

    dataset = Dataset(
        name=name,
        description=description,
        data_file_path=data_file_path,
        labels_file_path=labels_file_path,
        ammount_benign=benign,
        ammount_malicious=malicious,
        dataset_type_id=dataset_type.id
    )
    await add_dataset(db, dataset)

async def save_file_to_disk(file, path):
    with open(path, "wb") as f:
        f.write(file)
    
def remove_directory(path):
    try:
        shutil.rmtree(path)
    except Exception as e:
        LOGGER.error(e)
        
async def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_item_counts_of_dict(d: dict):
    """
    Method that returns the ammount of items stored in a dict, regardless of the keys
    """
    items = 0
    for _,v in d.items():
        items += len(v)
    return items

async def calculate_evaluation_metrics_and_push(db, dataset_id: int, alerts: list[Alert], container_name: str = None, ensemble_name: str = None):
    from .metrics import calculate_evaluation_metrics
    from .models.dataset import get_dataset_by_id
    # necessary to only pass the id here, as otherwise the db context will be closed on the next function call
    # and an error will be thrown
    dataset = await get_dataset_by_id(db, dataset_id)
    metrics = await calculate_evaluation_metrics(db, dataset_id, alerts)
    await push_evaluation_metrics_to_prometheus(metrics, container_name=container_name, dataset_name=dataset.name, ensemble_name=ensemble_name)   
    await db.close()

def extract_ts_srcip_srcport_dstip_dstport_from_alert(alert: Alert):
    source_ip = alert.source_ip.strip()
    source_port = alert.source_port.strip()
    destination_ip = alert.destination_ip.strip()
    destination_port = alert.destination_port.strip()
    timestamp = normalize_and_parse_alert_timestamp(alert.time)
    timestamp = timestamp.strip()
    return timestamp, source_ip, source_port, destination_ip, destination_port


def normalize_and_parse_alert_timestamp(timestamp_str) -> str:
    """
    Method to normalize timestamp formats, as these can differ from dataset to dataset
    Returns a normalized timestamp in minutes format (isoformat)

    IMPORTANT: The csv file and pcap file/alerts from the IDSs are expected to have timestamp in isoformat format
                Otherwise the processsing here won't work correctly
    """
    parsed_timestamp = parser.parse(timestamp_str).replace(tzinfo=None).isoformat().rsplit(":",maxsplit=1)[0]
    return parsed_timestamp



def get_length_of_nested_dict(d: dict):
    counter = 0
    for k,v in d.items():
        for container, alerts in v.items():
            counter += len(alerts)
    return counter


async def read_data_file(file_path):
    async with aiofiles.open(file_path, 'rb') as file:
        data_file = await file.read()
        return data_file
    

def directory_is_empty(path):
    return True if len(os.listdir(path)) == 0 else False