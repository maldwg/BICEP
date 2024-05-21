from pydantic import BaseModel

class IdsContainerCreate(BaseModel):
    """
        Class to validate input from the frontend
    """
    host: str
    description: str
    configurationId: int
    idsToolId: int


class ConfigurationCreate(BaseModel):
    """
        Class to validate confgiuration creation inputs
        the fuile upload is handled seperately
    """
    name: str
    description: str
