import base64
from http.client import HTTPResponse
import socket
from contextlib import closing
from enum import Enum
import os
import httpx
from fastapi import Response

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
        response: HTTPResponse = await client.post(container_url+endpoint,files=form_data)    
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