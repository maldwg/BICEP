import asyncio
import base64
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
from .prometheus import push_evaluation_metrics_to_prometheus
from .models.dataset import Dataset
from .bicep_utils.models.ids_base import Alert
from dateutil import parser
import uuid
import shutil
from fastapi.responses import JSONResponse

# global tasks dict that stores ids for stream tasks in containers 
# stream_metric_tasks = {

# }

def get_stream_metric_tasks(request: Request):
    return request.app.state.stream_metric_tasks

dataset_addition_tasks = set()

# asnycion craete task
class STATUS(Enum):
    ACTIVE = "active"
    IDLE = "idle"


class ANALYSIS_STATUS(Enum):
    LOGS_SENT = "LOGS_SENT"
    PROCESSING = "PROCESSING"
    IDLE = "IDLE"

class FILE_TYPES(Enum):
    CONFIG = "configuration"
    TEST_DATA = "test-data"
    RULE_SET = "rule-set"


class IdsContainerBase(object):

    def __init__(self, url: str, port: int, status: str, configuration_id: int, ids_tool_id: int, description: str = ""):
        """
            Default constructor with all parameters set
        """

        self.url = url
        self.port = port
        self.status = status
        self.configuration_id = configuration_id
        self.ids_tool_id = ids_tool_id

        # optional arguments
        if(description != ""):
            self.description = description

    @classmethod
    def initFromFrontend(self, configuration_id: str, ids_tool_id: str, description: str = ""):
        """
            Constructor for values received by the frontend (no status, url and port)
        """

        self.configuration_id = configuration_id
        self.ids_tool_id = ids_tool_id

        # optional arguments
        if(description != ""):
            self.description = description




def find_free_port():
    # TODO 10: Adapt this to also find free ports on other systems
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
                with open(dataset.pcap_file_path, "rb") as f:
                    form_data["dataset"] = (dataset.name, f, "application/octet-stream")
                    # set timeout to 600 seconds, as uploads can take a while
                    response = await client.post(container_url+endpoint,files=form_data, timeout=180)    
                    response.raise_for_status()
        except Exception as e:
            print(e)
    task = asyncio.create_task(send_request_in_background())
    print(task)
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

async def parse_response_for_triggered_analysis(response: HTTPResponse, container, db, analysis_type: str, ensemble_id: int = None):
    if response.status_code == 200:
        # await update_container_status(STATUS.ACTIVE.value, container, db)
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


async def calculate_benign_and_malicious_ammount(labels_file):
    # convert bytes to bytestream to be able to read it into pandas
    byte_stream = io.BytesIO(labels_file)
    df = pd.read_csv(byte_stream)

    df = df.map(lambda x: x.lower() if isinstance(x, str) else x)
    benign_count = df.apply(lambda row: row.str.contains('benign', na=False).any(), axis=1).sum()
    malicious_count = df.apply(lambda row: row.str.contains('malicious', na=False).any(), axis=1).sum()
    
    print(benign_count)
    print(malicious_count)
    return benign_count, malicious_count


async def dataset_callback(pcap_file, labels_file, name, description, db, future):
    from .models.dataset import Dataset, add_dataset
    try:
        benign, malicious = future.result()
        print(benign)
        print(malicious)
    except Exception as e:
        print("Task raised an exception:")

    dataset = Dataset(
        name=name,
        description=description,
        pcap_file=pcap_file,
        labels_file=labels_file,
        ammount_benign=benign,
        ammount_malicious=malicious,
    )
    add_dataset(db, dataset)
        
    dataset_addition_tasks.discard(future)


async def calculate_and_add_dataset(pcap_file, labels_file, name, description, db):
    from .models.dataset import Dataset, add_dataset
    byte_stream = io.BytesIO(labels_file)
    text_stream = io.TextIOWrapper(byte_stream, encoding='utf-8')
    
    benign, malicious = await calculate_malicious_benign_counts(text_stream)

    uid = str(uuid.uuid4())
    base_path = "/opt"
    dataset_storage_location = f"{base_path}/{name}/{uid}"
    
    pcap_file_path = f"{dataset_storage_location}/dataset.pcap"
    labels_file_path = f"{dataset_storage_location}/dataset.csv"

    await create_directory(dataset_storage_location)
    await save_file_to_disk(pcap_file, pcap_file_path)
    await save_file_to_disk(labels_file, labels_file_path)

    dataset = Dataset(
        name=name,
        description=description,
        pcap_file_path=pcap_file_path,
        labels_file_path=labels_file_path,
        ammount_benign=benign,
        ammount_malicious=malicious,
    )
    add_dataset(db, dataset)

async def save_file_to_disk(file, path):
    with open(path, "wb") as f:
        f.write(file)
    
def remove_directory(path):
    print(path)
    try:
        shutil.rmtree(path)
    except Exception as e:
        print(e)
        
async def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Efficient CSV processing using a genrator
async def calculate_malicious_benign_counts(input_file):
    benign_count = 0
    malicious_count = 0
    header = True
    with input_file as input_csv:
        reader = csv.reader(input_csv)
        for row in reader:
            if header:
                header = False
                continue
            # Convert each cell in the row to lowercase and check for "benign"
            if any("benign" in cell.lower() for cell in row):
                benign_count += 1
            else:
                malicious_count += 1

    return benign_count, malicious_count

def get_serialized_datasets(datasets):
    serialized_datasets = []
    for dataset in datasets:
        serialized_config = {
            "id": dataset.id,
            "name": dataset.name,
            "pcap_file_path": dataset.pcap_file_path, 
            "labels_file_path": dataset.labels_file_path,  
            "description": dataset.description,
            "ammount_benign": dataset.ammount_benign,
            "ammount_malicious": dataset.ammount_malicious

        }
        serialized_datasets.append(serialized_config)
    return serialized_datasets

async def calculate_evaluation_metrics_and_push(dataset: Dataset, alerts: list[Alert], container_name: str):
    from .metrics import calculate_evaluation_metrics
    metrics = await calculate_evaluation_metrics(dataset, alerts)
    await push_evaluation_metrics_to_prometheus(metrics, container_name=container_name, dataset_name=dataset.name)   


async def extract_ts_srcip_srcport_dstip_dstport_from_alert(alert: Alert):
    source_ip = alert.source_ip.strip()
    source_port = alert.source_port.strip()
    destination_ip = alert.destination_ip.strip()
    destination_port = alert.destination_port.strip()
    timestamp = await normalize_and_parse_alert_timestamp(alert.time)
    timestamp = timestamp.strip()
    return timestamp, source_ip, source_port, destination_ip, destination_port


async def normalize_and_parse_alert_timestamp(timestamp_str) -> str:
    """
    Method to normalize timestamp formats, as these can differ from dataset to dataset
    Returns a normalized timestamp in minutes format (isoformat)

    IMPORTANT: The csv file and pcap file/alerts from the IDSs are expected to have timestamp in isoformat format
                Otherwise the processsing here won't work correctly
    """
    parsed_timestamp = parser.parse(timestamp_str).replace(tzinfo=None).isoformat().rsplit(":",maxsplit=1)[0]
    return parsed_timestamp

async def combine_alerts_for_ids_in_alert_dict(alerts_dict: dict) -> dict:
    """
        Gets a dict of this shape: {"ids": list[Alert], "ids2": list[Alert], ...}
        returns a dict like : {ts-src_ip-src_port-dst_ip-dst_port: {"ids1": list[Alert], "ids2": list[Alert]}}
    """
    common_alerts = {}
    for container_name, alerts in alerts_dict.items():
        for alert in alerts:
            timestamp, source_ip, source_port, destination_ip, destination_port = await extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)
            key = (timestamp, source_ip, source_port, destination_ip, destination_port)
            common_alerts.setdefault(key, {}).setdefault(container_name, []).extend([alert])
            # check if alert is already in dict, and increment counter for container detecting it
            # common_alerts_for_key = common_alerts.get(key, {})
            # if common_alerts_for_key == {}:
            #     initial_container_alert_dict = {container_name: [alert]}
            #     common_alerts[key] = initial_container_alert_dict
            # else:
            #     common_alerts[key][container_name] = common_alerts.get(key, {}).get(container_name, []) + [alert]
    return common_alerts