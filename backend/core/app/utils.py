import asyncio
import base64
from http.client import HTTPResponse
import io
import socket
from contextlib import closing
from enum import Enum
import os
import httpx
from fastapi import Response
import pandas as pd
import multiprocessing
import csv 
import time 
from .prometheus import push_evaluation_metrics_to_prometheus
from .metrics import calculate_evaluation_metrics
from .models.dataset import Dataset
from .bicep_utils.models.ids_base import Alert
# global tasks dict that stores ids for stream tasks in containers 
stream_metric_tasks = {

}

dataset_addition_tasks = set()

# TODO 5: find a way to make it asynch --> maybe backroung task with asynchio in the endpoint ?

# asnycion craete task
class STATUS(Enum):
    ACTIVE = "active"
    IDLE = "idle"


class FILE_TYPES(Enum):
    CONFIG = "configuration"
    TEST_DATA = "test-data"
    RULE_SET = "rule-set"
class Ids(object):
    name = ""
    image = ""
    config_path=""

# TODO: refactor so that image is in the table not here
# TODO: config path is in ids logic not here
class Suricata(Ids):
    name = "Suricata"
    image = "maxldwg/bicep-suricata"
    config_path = "/opt/suricata.yaml"

class Slips(Ids):
    name = "Slips"
    image = "maxldwg/bicep-slips"
    config_path = "/opt/slips.yaml"



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
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
    

def get_core_host():
    return os.popen("/sbin/ip route|awk '/default/ { print $3 }'").read().strip()

def get_container_host(ids_container):
    if ids_container.host != "localhost":
        return ids_container.host
    else:
        return get_core_host()
    

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
    host = get_container_host(container)
    container_url = f"http://{host}:{container.port}"
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


async def start_static_analysis(container, form_data):
    endpoint = "/analysis/static"
    host = get_container_host(container)
    container_url = f"http://{host}:{container.port}"
    async with httpx.AsyncClient() as client:  
        # set timeout to 90 seconds, as uploads can take a while
        response: HTTPResponse = await client.post(container_url+endpoint,files=form_data, timeout=90)    
    return response

async def start_network_analysis(container, data):
    endpoint = "/analysis/network"
    host = get_container_host(container)
    container_url = f"http://{host}:{container.port}"
    async with httpx.AsyncClient() as client:
        response = await client.post(container_url+endpoint, data=data)
    return response

async def stop_analysis(container):
    host = get_container_host(container)
    container_url = f"http://{host}:{container.port}"
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


def calculate_cpu_percent(previous_cpu, previous_system, current_cpu, current_system, online_cpus):
    cpu_delta = current_cpu - previous_cpu
    system_delta = current_system - previous_system
    
    if system_delta > 0 and cpu_delta > 0:
        return (cpu_delta / system_delta) * online_cpus * 100.0
    return 0.0

# TODO 8: add calculation
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

    dataset = Dataset(
        name=name,
        description=description,
        pcap_file=pcap_file,
        labels_file=labels_file,
        ammount_benign=benign,
        ammount_malicious=malicious,
    )
    add_dataset(db, dataset)

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
    serialized_configs = []
    for dataset in datasets:
        serialized_config = {
            "id": dataset.id,
            "name": dataset.name,
            "pcap_file": base64.b64encode(dataset.pcap_file).decode('utf-8'),  # Encode binary data to Base64, otherwise error when returning pcap files 
            "labels_file": base64.b64encode(dataset.labels_file).decode('utf-8'),  # Encode binary data to Base64, otherwise error when returning pcap files 
            "description": dataset.description,
            "ammount_benign": dataset.ammount_benign,
            "ammount_malicious": dataset.ammount_malicious

        }
        serialized_configs.append(serialized_config)
    return serialized_configs

async def calculate_evaluation_metrics_and_push(dataset: Dataset, alerts: list[Alert], container_name: str):
    metrics = await calculate_evaluation_metrics(dataset, alerts)
    await push_evaluation_metrics_to_prometheus(metrics, container_name=container_name, dataset_name=dataset.name)