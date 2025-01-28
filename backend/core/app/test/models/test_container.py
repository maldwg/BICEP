import pytest
from docker import DockerClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.test.fixtures import *
from app.models.ids_container import *
from app.utils import STATUS


@pytest.fixture
def mock_ids_container():
    ids_container = IdsContainer(
        id = 1,
        name = "Test IDS",
        port = 8080,
        status = STATUS.IDLE.value,
        description = "Test Description",
        stream_metric_task_id = None,
        configuration_id = 1,
        ids_tool_id = 1,
        ruleset_id = 1,
        host_system_id = 1
    )
    return ids_container
