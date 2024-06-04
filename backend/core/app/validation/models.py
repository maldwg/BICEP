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
    container_id: int
    dataset_id: int

class StaticAnalysisEnsembleData(BaseModel):
    """

    """
    ensemble_id: int
    dataset_id: int

class NetworkAnalysisData(BaseModel):
    """

    """
    container_id: int

class NetworkAnalysisEnsembleData(BaseModel):
    """

    """
    ensemble_id: int
    dataset_id: int

class StopAnalysisData(BaseModel):
    """
    
    """
    container_id: int

class StopAnalysisEnsembleData(BaseModel):
    """
    
    """
    ensemble_id: int