import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.routers.ids import *
from app.validation.models import *
from app.models.docker_host_system import DockerHostSystem
from app.models.ids_tool import IdsTool
from app.models.configuration import Configuration
from app.models.dataset import Dataset
from sqlalchemy.orm import Session

TESTS_BASE_DIR = "./backend/core/app/test"

class DatabaseSessionFixture():
    
    db_session: Session 
    mock_docker_host_system: MagicMock
    mock_ids_container: AsyncMock
    mock_ids_tool: MagicMock
    mock_configuration: MagicMock
    mock_dataset: MagicMock
    mock_ruleset: MagicMock()

    def __init__(self, db_session, mock_docker_host_system, mock_ids_container, mock_ids_tool, mock_configuration, mock_ruleset, mock_dataset):
        self.db_session = db_session
        self.mock_docker_host_system = mock_docker_host_system
        self.mock_ids_container = mock_ids_container
        self.mock_ids_tool = mock_ids_tool
        self.mock_configuration = mock_configuration
        self.mock_ruleset = mock_ruleset
        self.mock_dataset = mock_dataset

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
        pass
    def get_ensemble_technique_model(self):
        pass
    def get_ids_container_model(self):
        return self.mock_ids_container
    
    def get_ids_tool_model(self):
        return self.mock_ids_tool


@pytest.fixture
def db_session_fixture():
    # Create the mock database session
    mock_db = MagicMock()

    # Create the mock DockerHostSystem object
    mock_docker_host_system = MagicMock(spec=DockerHostSystem)
    mock_docker_host_system.id = 1
    mock_docker_host_system.name = "localhost"

    mock_dataset = MagicMock(spec=Dataset)
    mock_dataset.id = 1
    mock_dataset.name = "Test Dataset"
    second_mock_dataset = MagicMock(spec=Dataset)
    second_mock_dataset.name = "Test Dataset 2"

    mock_configuration = MagicMock(spec=Configuration)
    mock_configuration.id = 1
    mock_configuration.name = "test-config 1"
    mock_configuration.file_type = "configuration"
    mock_configuration.configuration = open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml","rb").read()
    mock_configuration_ruleset = MagicMock(spec=Configuration)
    mock_configuration_ruleset.id = 2
    mock_configuration_ruleset.name = "test-config 2"
    mock_configuration_ruleset.file_type = "rule-set"
    mock_configuration_ruleset.configuration = open(f"{TESTS_BASE_DIR}/testfiles/test-config.yaml","rb").read()

    mock_ids_tool = MagicMock(spec=IdsTool)
    mock_ids_tool.id = 1
    mock_ids_tool.name = "Suricata"
    second_mock_ids_tool = MagicMock(spec=IdsTool)
    second_mock_ids_tool.id = 2
    second_mock_ids_tool.name = "Slips"

    mock_ids_container = AsyncMock(spec=IdsContainer)
    mock_ids_container.id = 1 
    mock_ids_container.status = STATUS.IDLE.value
    mock_ids_container.ids_tool_id = 1
    mock_ids_container.name = "container-0"
    mock_ids_container.description = "Test description"
    mock_ids_container.host_system = mock_docker_host_system
    mock_ids_container.stop_metric_collection = AsyncMock()
    mock_ids_container.start_metric_collection = AsyncMock()
    mock_ids_container.setup = AsyncMock()
    mock_ids_container.stop_analysis = AsyncMock()
    mock_ids_container.teardown = AsyncMock()
    mock_ids_container.start_static_analysis = AsyncMock()
    mock_ids_container.start_network_analysis = AsyncMock()

    def query_side_effect(model):
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        if model == DockerHostSystem:
            mock_filter.first.return_value = mock_docker_host_system
        elif model == IdsContainer:
            mock_filter.first.return_value = mock_ids_container
            mock_query.all.return_value = [mock_ids_container]
        elif model == IdsTool:
            mock_filter.first.return_value = mock_ids_tool
            mock_query.all.return_value = [mock_ids_tool, second_mock_ids_tool]
        elif model == Configuration:
            mock_filter.first.return_value = mock_configuration
            # mock_query.all is necessray since it is db.query.all and not db.query.filter.all
            mock_query.all.return_value = [mock_configuration, mock_configuration_ruleset]
            # for db.query.filter(filetype).all
            mock_filter.all.return_value = [mock_configuration_ruleset]
            # 
        elif model == Dataset:
            mock_filter.first.return_value = mock_dataset
            mock_query.all.return_value = [mock_dataset, second_mock_dataset]
        else:
            raise ValueError(f"Unsupported model: {model}")
        return mock_query

    # Configure the `query` method of the mock db session
    mock_db.query.side_effect = query_side_effect

    db_fixture: DatabaseSessionFixture = DatabaseSessionFixture(
        db_session=mock_db,
        mock_docker_host_system=mock_docker_host_system,
        mock_ids_container=mock_ids_container,
        mock_ids_tool=mock_ids_tool,
        mock_configuration=mock_configuration,
        mock_ruleset=mock_configuration_ruleset,
        mock_dataset=mock_dataset
    )

    # Yield the mock session
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
