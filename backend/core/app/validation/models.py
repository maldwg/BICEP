from pydantic import BaseModel

class IdsContainerCreate(BaseModel):
    """
        Class to validate input from the frontend
    """
    host: str
    description: str
    configurationId: int
    idsToolId: int