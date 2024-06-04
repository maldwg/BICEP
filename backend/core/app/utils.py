import socket
from contextlib import closing
from enum import Enum
import os 
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
    

