import socket
from contextlib import closing
from enum import Enum

class STATUS(Enum):
    ACTIVE = "active"
    IDLE = "idle"

class Ids(object):
    name = ""
    image = ""
    config_path=""

class Suricata(Ids):
    name = "suricata"
    image = "maxldwg/bicep-suricata"
    config_path = "/opt/suricata.yaml"

class Slips(Ids):
    name = "slips"
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
    

