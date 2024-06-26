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

class IdsContainerUpdate(BaseModel):
    """
        Class to validate input from the frontend
    """
    id: int
    description: str
    configuration_id: int
    ruleset_id: Optional[int] = None

class EnsembleCreate(BaseModel):
    """
    Class to validate input for Ensemble creation
    """

    name: str
    description: str
    technique: int
    container_ids: list[int]

class EnsembleUpdate(BaseModel):
    """
    Class to validate input for Ensemble creation
    """
    id: int
    name: str
    description: str
    technique_id: int
    container_ids: list[int]


class StaticAnalysisData(BaseModel):
    """

    """
    container_id: Optional[int] = None
    ensemble_id: Optional[int] = None
    dataset_id: int

class NetworkAnalysisData(BaseModel):
    """

    """
    container_id: Optional[int] = None
    ensemble_id: Optional[int] = None

class StopAnalysisData(BaseModel):
    """
    
    """
    container_id: Optional[int] = None
    ensemble_id: Optional[int] = None