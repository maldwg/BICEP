from pydantic import BaseModel

class IdsContainerCreate(BaseModel):
    """
        Class to validate input from the frontend
    """
    url: str
    description: str
    configuration_id: int
    ids_tool_id: int