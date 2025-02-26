import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.routers.ids import *
from app.validation.models import *
from app.models.docker_host_system import DockerHostSystem
from app.models.ids_tool import IdsTool
from app.models.configuration import Configuration
from app.models.dataset import Dataset
from app.models.ensemble import Ensemble
from app.models.ensemble_ids import EnsembleIds
from app.models.ensemble_technique import EnsembleTechnique
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dataset_types import DatasetType
from sqlalchemy.sql.selectable import Select
import pytest_asyncio

TESTS_BASE_DIR = "./backend/core/app/test"

class DatabaseSessionFixture():
    
    db_session: AsyncSession 
    mock_docker_host_system: MagicMock
    mock_ids_container: AsyncMock
    mock_ids_tool: MagicMock
    mock_configuration: MagicMock
    mock_dataset: MagicMock
    mock_ruleset: MagicMock
    mock_ensemble: MagicMock
    mock_ensemble_ids: MagicMock
    mock_ensemble_technique: MagicMock
    mock_dataset_type: MagicMock

    def __init__(
            self,
            db_session, 
            mock_docker_host_system,
            mock_ids_container, 
            mock_ids_tool, 
            mock_configuration, 
            mock_ruleset, 
            mock_dataset, 
            mock_ensemble, 
            mock_ensemble_ids,
            mock_ensemble_technique,
            mock_dataset_type
        ):
        self.db_session = db_session
        self.mock_docker_host_system = mock_docker_host_system
        self.mock_ids_container = mock_ids_container
        self.mock_ids_tool = mock_ids_tool
        self.mock_configuration = mock_configuration
        self.mock_ruleset = mock_ruleset
        self.mock_dataset = mock_dataset
        self.mock_ensemble = mock_ensemble
        self.mock_ensemble_ids = mock_ensemble_ids
        self.mock_ensemble_technique = mock_ensemble_technique
        self.mock_dataset_type = mock_dataset_type

    def get_db_session(self):
        return self.db_session
    
    def get_configuration_model(self):
        return self.mock_configuration
    
    def get_ruleset_model(self):
        return self.mock_ruleset
    
    def get_dataset_model(self):
        return self.mock_dataset
    
    def get_docker_host_system_model(self):
        return self.mock_docker_host_system
    
    def get_ensemble_ids_model(self):
        return self.mock_ensemble_ids
    
    def get_ensemble_technique_model(self):
        return self.mock_ensemble_technique
    
    def get_ids_container_model(self):
        return self.mock_ids_container
    
    def get_ids_tool_model(self):
        return self.mock_ids_tool
    
    def get_ensemble_model(self):
        return self.mock_ensemble
    def get_dataset_type_model(self):
        return self.mock_dataset_type


@pytest_asyncio.fixture
async def db_session_fixture():
    mock_db = AsyncMock(spec=AsyncSession)

    mock_docker_host_system = MagicMock(spec=DockerHostSystem, id=1, name="localhost")
    mock_dataset_type = MagicMock(spec=DatasetType, id=1, name="network_traffic_data")
    mock_dataset_type.get_benign_and_malicious_counts = AsyncMock(return_value=(0, 1))
    mock_dataset = MagicMock(
            spec=Dataset,
            id=1,
            name="TestDataset", 
            description="Test dataset for IDS evaluation", 
            dataset_type=mock_dataset_type,
            data_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.pcap",
            labels_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.csv",
            ammount_benign=899,
            ammount_malicious=100,
            dataset_type_id = 1,
        )
    
    second_mock_dataset = MagicMock(spec=Dataset, id=2, name="Test Dataset 2")


    mock_configuration = MagicMock(
        spec=Configuration,
        id=1,
        name="test-config 1",
        file_type="configuration",
        configuration=open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml", "rb").read()
    )
    mock_configuration_ruleset = MagicMock(
        spec=Configuration,
        id=2,
        name="test-config 2",
        file_type="rule-set",
        configuration=open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml", "rb").read()
    )

    mock_ids_tool = MagicMock(spec=IdsTool, id=1, name="Suricata")
    second_mock_ids_tool = MagicMock(spec=IdsTool, id=2, name="Slips")

    mock_ids_container = AsyncMock(spec=IdsContainer, id=1, status=STATUS.IDLE.value, name="container-0")
    mock_ids_container.host_system = mock_docker_host_system
    mock_ids_container.is_available = AsyncMock(return_value=True)
    mock_ids_container.is_busy = AsyncMock(return_value=True)

    mock_ensemble_technique = MagicMock(spec=EnsembleTechnique, id=1, function_name="majority_vote")
    mock_ensemble_technique.execute_technique_by_name_on_alerts = AsyncMock()

    mock_ensemble = AsyncMock(spec=Ensemble, id=1, name="Ensemble-1", ensemble_technique=mock_ensemble_technique)
    mock_ensemble_ids = MagicMock(spec=EnsembleIds, id=1, ensemble_id=1, ids_container_id=1)

    async def execute_side_effect(stmt):
        if isinstance(stmt, Select):
            model = stmt.column_descriptions[0]['type']
            if model == DockerHostSystem:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_docker_host_system), scalars=AsyncMock(return_value=[mock_docker_host_system]))
            elif model == IdsContainer:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_ids_container), scalars=AsyncMock(return_value=[mock_ids_container]))
            elif model == IdsTool:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_ids_tool), scalars=AsyncMock(return_value=[mock_ids_tool, second_mock_ids_tool]))
            elif model == Configuration:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_configuration), scalars=AsyncMock(return_value=[mock_configuration, mock_configuration_ruleset]))
            elif model == Dataset:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_dataset), scalars=AsyncMock(return_value=[mock_dataset, second_mock_dataset]))
            elif model == Ensemble:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_ensemble))
            elif model == EnsembleTechnique:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_ensemble_technique), scalars=AsyncMock(return_value=[mock_ensemble_technique]))
            elif model == EnsembleIds:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_ensemble_ids), scalars=AsyncMock(return_value=[mock_ensemble_ids]))
            elif model == DatasetType:
                return MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_dataset_type), scalars=AsyncMock(return_value=[mock_dataset_type]))
        raise ValueError(f"Unsupported query: {stmt}")
    
    mock_db.execute.side_effect = execute_side_effect

    db_fixture = DatabaseSessionFixture(
        db_session=mock_db,
        mock_docker_host_system=mock_docker_host_system,
        mock_ids_container=mock_ids_container,
        mock_ids_tool=mock_ids_tool,
        mock_configuration=mock_configuration,
        mock_ruleset=mock_configuration_ruleset,
        mock_dataset=mock_dataset,
        mock_ensemble=mock_ensemble,
        mock_ensemble_ids=mock_ensemble_ids,
        mock_ensemble_technique=mock_ensemble_technique,
        mock_dataset_type=mock_dataset_type
    )
    yield db_fixture

@pytest.fixture
def mock_stream_metric_tasks():
    return AsyncMock()

@pytest.fixture
def mock_background_tasks():
    """
    Mock the BackgroundTasks instance.
    """
    tasks = MagicMock(spec=set())
    tasks.add_task = MagicMock()
    return tasks


@pytest.fixture
def mock_alerts():
    alert1 = Alert(
                    time= "2025-01-01T12:00:00Z",
                    destination_ip= "192.168.0.1",
                    destination_port= "8080",
                    source_ip= "10.0.0.1",
                    source_port= "1234",
                    severity= 0,
                    type= "test alert",
                    message = "Test alert message"
        )
    alert2 = Alert(
                    time= "2025-01-01T13:00:00Z",
                    destination_ip= "169.168.0.1",
                    destination_port= "3200",
                    source_ip= "10.0.0.1",
                    source_port= "1234",
                    severity= 1,
                    type= "test alert 2",
                    message = "Test alert 2 message"
        )
    alert3 = Alert(
                    time= "2025-01-01T14:00:00Z",
                    destination_ip= "0.0.0.1",
                    destination_port= "10230",
                    source_ip= "10.0.0.1",
                    source_port= "5678",
                    severity= 0,
                    type= "test alert 3",
                    message = "Test alert 3 message"
        )
    return [alert1,alert2,alert3]