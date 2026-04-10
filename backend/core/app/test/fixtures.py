import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
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
from app.models.benchmarking import BenchmarkingIntermediateResult
from app.utils import DEPLOYMENT_STATUS
import pytest_asyncio

TESTS_BASE_DIR = Path(__file__).resolve().parent


class DatabaseSessionFixture:

    db_session: AsyncSession
    mock_docker_host_system: MagicMock
    mock_ids_container: MagicMock
    mock_ids_tool: MagicMock
    mock_configuration: MagicMock
    mock_dataset: MagicMock
    mock_ruleset: MagicMock
    mock_ensemble: MagicMock
    mock_ensemble_ids: MagicMock
    mock_ensemble_technique: MagicMock
    mock_dataset_type: MagicMock
    mock_benchmarking_intermediate_result: MagicMock

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
        mock_dataset_type,
        mock_benchmarking_intermediate_result,
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
        self.mock_benchmarking_intermediate_result = (
            mock_benchmarking_intermediate_result
        )

    async def get_db_session(self):
        return self.db_session

    async def get_configuration_model(self):
        return self.mock_configuration

    async def get_ruleset_model(self):
        return self.mock_ruleset

    async def get_dataset_model(self):
        return self.mock_dataset

    async def get_docker_host_system_model(self):
        return self.mock_docker_host_system

    async def get_ensemble_ids_model(self):
        return self.mock_ensemble_ids

    async def get_ensemble_technique_model(self):
        return self.mock_ensemble_technique

    async def get_ids_container_model(self):
        return self.mock_ids_container

    async def get_ids_tool_model(self):
        return self.mock_ids_tool

    async def get_ensemble_model(self):
        return self.mock_ensemble

    async def get_dataset_type_model(self):
        return self.mock_dataset_type


@pytest_asyncio.fixture
async def db_session_fixture():
    mock_db = AsyncMock(spec=AsyncSession)

    mock_docker_host_system = MagicMock(spec=DockerHostSystem)
    mock_docker_host_system.id = 1
    mock_docker_host_system.name = "localhost"
    mock_docker_host_system.host = "localhost"
    mock_docker_host_system.docker_port = 2375
    mock_docker_host_system.status = "available"
    mock_docker_host_system.metric_service = None

    mock_dataset_type = MagicMock(spec=DatasetType)
    mock_dataset_type.id = 1
    mock_dataset_type.name = "network_traffic_data"
    mock_dataset_type.get_benign_and_malicious_counts = AsyncMock(
        return_value=(899, 100)
    )
    mock_dataset_type.get_positives_and_negatives_from_dataset = AsyncMock(
        return_value=(9, 6, 893, 91, 0, 15)
    )
    mock_dataset = MagicMock(spec=Dataset)
    mock_dataset.id = 1
    mock_dataset.name = "TestDataset"
    mock_dataset.description = "Test dataset for IDS evaluation"
    mock_dataset.dataset_type = mock_dataset_type
    mock_dataset.data_file_path = f"{TESTS_BASE_DIR}/testfiles/sample_data.pcap"
    mock_dataset.labels_file_path = f"{TESTS_BASE_DIR}/testfiles/sample_data.csv"
    mock_dataset.ammount_benign = 899
    mock_dataset.ammount_malicious = 100
    mock_dataset.dataset_type_id = 1
    mock_dataset.timestamp_precision = "minute"

    second_mock_dataset = MagicMock(spec=Dataset)
    second_mock_dataset.id = 2
    second_mock_dataset.name = "Test Dataset 2"
    second_mock_dataset.timestamp_precision = "second"

    mock_configuration = MagicMock(spec=Configuration)
    mock_configuration.id = (1,)
    mock_configuration.name = "test-config 1"
    mock_configuration.file_type = "RUNTIME"
    mock_configuration.file_path = f"{TESTS_BASE_DIR}/testfiles/test-config.yaml"
    file_content = open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml", "rb").read()
    mock_configuration.read_content = AsyncMock(return_value=file_content)
    mock_configuration_ruleset = MagicMock(SPEC=Configuration)
    mock_configuration_ruleset.id = 2
    mock_configuration_ruleset.name = "test-config 2"
    mock_configuration_ruleset.file_type = "RULESET"
    mock_configuration_ruleset.file_path = (
        f"{TESTS_BASE_DIR}/testfiles/test-config.yaml"
    )
    file_content = open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml", "rb").read()
    mock_configuration_ruleset.read_content = AsyncMock(return_value=file_content)

    mock_ids_tool = MagicMock(spec=IdsTool)
    mock_ids_tool.id = 1
    mock_ids_tool.name = "Suricata"
    mock_ids_tool.deployment_type = "SINGLE_CONTAINER"
    second_mock_ids_tool = MagicMock(spec=IdsTool)
    second_mock_ids_tool.id = (2,)
    second_mock_ids_tool.name = "Slips"
    second_mock_ids_tool.deployment_type = "SINGLE_CONTAINER"

    mock_ids_container = MagicMock(spec=IdsSystem)
    mock_ids_container.id = 1
    mock_ids_container.status = STATUS.IDLE.value
    mock_ids_container.name = "container-0"
    mock_ids_container.configuration_id = 1
    mock_ids_container.ruleset_id = 2
    mock_ids_container.description = "Test description"
    mock_ids_container.deployment_status = DEPLOYMENT_STATUS.DEPLOYED.value
    mock_ids_container.host_system = mock_docker_host_system
    mock_ids_container.is_available = AsyncMock(return_value=True)
    mock_ids_container.is_busy = AsyncMock(return_value=True)
    mock_ids_container.ensemble_ids = []

    mock_ensemble_technique = MagicMock(spec=EnsembleTechnique)
    mock_ensemble_technique.id = 1
    mock_ensemble_technique.function_name = "majority_vote"
    mock_ensemble_technique.execute_technique_by_name_on_alerts = AsyncMock()

    mock_ensemble = MagicMock(spec=Ensemble)
    mock_ensemble.id = 1
    mock_ensemble.name = "Ensemble-1"
    mock_ensemble.description = "Test-Description"
    mock_ensemble.ensemble_technique = mock_ensemble_technique
    mock_ensemble_ids = MagicMock(spec=EnsembleIds)
    mock_ensemble_ids.id = 1
    mock_ensemble_ids.ensemble_id = 1
    mock_ensemble_ids.ids_system_id = 3
    mock_ensemble.technique_id = 1

    mock_ids_container_in_ensemble = MagicMock(spec=IdsSystem)
    mock_ids_container_in_ensemble.id = 3
    mock_ids_container_in_ensemble.status = STATUS.IDLE.value
    mock_ids_container_in_ensemble.name = "container-3"
    mock_ids_container_in_ensemble.configuration_id = 1
    mock_ids_container_in_ensemble.ruleset_id = 2
    mock_ids_container_in_ensemble.description = "Test description"
    mock_ids_container_in_ensemble.deployment_status = (
        DEPLOYMENT_STATUS.DEPLOYED.value
    )
    mock_ids_container_in_ensemble.host_system = mock_docker_host_system
    mock_ids_container_in_ensemble.is_available = AsyncMock(return_value=True)
    mock_ids_container_in_ensemble.is_busy = AsyncMock(return_value=True)
    mock_ids_container_in_ensemble.ensemble_ids = [mock_ensemble_ids]

    mock_benchmarking_intermediate_result = MagicMock(
        spec=BenchmarkingIntermediateResult
    )
    mock_benchmarking_intermediate_result.id = 1
    mock_benchmarking_intermediate_result.start_time = "01-01-2025 12:00:00.000000"
    mock_benchmarking_intermediate_result.stop_time = "01-01-2025 12:05:00.000000"

    async def execute_side_effect(stmt):
        if isinstance(stmt, Select):
            model = stmt.column_descriptions[0]["type"]

            mock_result = MagicMock()
            if model == DockerHostSystem:
                mock_result.scalar_one_or_none.return_value = mock_docker_host_system
                mock_result.scalars.return_value.all.return_value = [
                    mock_docker_host_system
                ]
            elif model == IdsSystem:
                mock_result.scalar_one_or_none.return_value = mock_ids_container
                mock_result.scalars.return_value.all.return_value = [mock_ids_container]
            elif model == IdsTool:
                mock_result.scalar_one_or_none.return_value = mock_ids_tool
                mock_result.scalars.return_value.all.return_value = [
                    mock_ids_tool,
                    second_mock_ids_tool,
                ]
            elif model == Configuration:
                mock_result.scalar_one_or_none.return_value = mock_configuration
                mock_result.scalars.return_value.all.return_value = [
                    mock_configuration,
                    mock_configuration_ruleset,
                ]
            elif model == Dataset:
                mock_result.scalar_one_or_none.return_value = mock_dataset
                mock_result.scalars.return_value.all.return_value = [
                    mock_dataset,
                    second_mock_dataset,
                ]
            elif model == Ensemble:
                mock_result.scalar_one_or_none.return_value = mock_ensemble
            elif model == EnsembleTechnique:
                mock_result.scalar_one_or_none.return_value = mock_ensemble_technique
                mock_result.scalars.return_value.all.return_value = [
                    mock_ensemble_technique
                ]
            elif model == EnsembleIds:
                mock_result.scalar_one_or_none.return_value = mock_ensemble_ids
                mock_result.scalars.return_value.all.return_value = [mock_ensemble_ids]
            elif model == DatasetType:
                mock_result.scalar_one_or_none.return_value = mock_dataset_type
                mock_result.scalars.return_value.all.return_value = [mock_dataset_type]
            elif model == BenchmarkingIntermediateResult:
                mock_result.scalar_one_or_none.return_value = (
                    mock_benchmarking_intermediate_result
                )
                mock_result.scalars.return_value.all.return_value = [
                    mock_benchmarking_intermediate_result
                ]
            else:
                raise ValueError(f"Unsupported query: {stmt}")

            return mock_result

        raise ValueError(f"Unsupported query type: {stmt}")

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
        mock_dataset_type=mock_dataset_type,
        mock_benchmarking_intermediate_result=mock_benchmarking_intermediate_result,
    )
    yield db_fixture


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
        time="2025-01-01T12:00:00Z",
        destination_ip="192.168.0.1",
        destination_port="8080",
        source_ip="10.0.0.1",
        source_port="1234",
        severity=0,
        type="test alert",
        message="Test alert message",
    )
    alert2 = Alert(
        time="2025-01-01T13:00:00Z",
        destination_ip="169.168.0.1",
        destination_port="3200",
        source_ip="10.0.0.1",
        source_port="1234",
        severity=1,
        type="test alert 2",
        message="Test alert 2 message",
    )
    alert3 = Alert(
        time="2025-01-01T14:00:00Z",
        destination_ip="0.0.0.1",
        destination_port="10230",
        source_ip="10.0.0.1",
        source_port="5678",
        severity=0,
        type="test alert 3",
        message="Test alert 3 message",
    )
    alert4 = Alert(
        time="2025-01-01T14:00:00Z",
        destination_ip="0.0.0.1",
        destination_port="10230",
        source_ip="10.0.0.1",
        source_port="5678",
        severity=0,
        type="test alert 4",
        message="Test alert 4 message",
    )
    return [alert1, alert2, alert3, alert4]
