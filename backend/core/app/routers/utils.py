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