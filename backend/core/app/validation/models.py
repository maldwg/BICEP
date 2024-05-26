from pydantic import BaseModel
from typing import Optional

class IdsContainerCreate(BaseModel):
    """
        Class to validate input from the frontend
    """
    host: str
    description: str
    configuration_id: int
    ids_tool_id: int
    ruleset_id: Optional[int] = None

class EnsembleCreate(BaseModel):
    """
    Class to validate input for Ensemble creation
    """

    name: str
    description: str
    technique: int
    container_ids: list[int]