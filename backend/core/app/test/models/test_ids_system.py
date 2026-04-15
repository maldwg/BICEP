import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.docker_host_system import DockerHostSystem
from app.models.ids_system import (
    IdsSystem,
    NidsSystem,
    HidsSystem,
    CidsSystem,
    get_ids_system_by_id,
    get_all_container,
    remove_container_by_id,
    update_ids_status,
    get_ids_system_model,
)
from app.models.ids_component import IdsComponent
from app.utils import DEPLOYMENT_STATUS, STATUS
from app.test.fixtures import *


# ==================== FIXTURES ====================


@pytest.fixture
def mock_host_system():
    return DockerHostSystem(
        id=1, name="Core Host", host="localhost", docker_port=2375
    )


@pytest.fixture
def mock_remote_host():
    return DockerHostSystem(
        id=2, name="Remote Worker", host="192.168.5.10", docker_port=2376
    )


@pytest.fixture
def nids_system(mock_host_system):
    return NidsSystem(
        id=1,
        name="Suricata-8080",
        port=8080,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        description="Test NIDS",
        configuration_id=1,
        ids_tool_id=1,
        host_system_id=1,
        host_system=mock_host_system,
        type="NIDS",
    )


@pytest.fixture
def hids_system(mock_host_system):
    return HidsSystem(
        id=2,
        name="Wazuh-8081",
        port=8081,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        description="Test HIDS",
        configuration_id=1,
        ids_tool_id=2,
        host_system_id=1,
        host_system=mock_host_system,
        type="HIDS",
    )


@pytest.fixture
def cids_system(mock_host_system):
    sensor = IdsComponent(
        id=10,
        ids_id=3,
        name="sensor-1",
        role="SENSOR",
        port=9090,
        host_system_id=None,
    )
    # Manually set the host_system since we're not using the DB
    sensor.host_system = None

    aggregator = IdsComponent(
        id=11,
        ids_id=3,
        name="aggregator-1",
        role="AGGREGATOR",
        port=9091,
        host_system_id=None,
    )
    aggregator.host_system = None

    cids = CidsSystem(
        id=3,
        name="CIDS-8082",
        port=8082,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        description="Test CIDS",
        configuration_id=1,
        ids_tool_id=3,
        host_system_id=1,
        host_system=mock_host_system,
        type="CIDS",
    )
    cids.components = [aggregator, sensor]
    return cids


# ==================== POLYMORPHIC IDENTITY ====================


def test_nids_polymorphic_identity(nids_system):
    assert nids_system.type == "NIDS"
    assert isinstance(nids_system, NidsSystem)
    assert isinstance(nids_system, IdsSystem)


def test_hids_polymorphic_identity(hids_system):
    assert hids_system.type == "HIDS"
    assert isinstance(hids_system, HidsSystem)
    assert isinstance(hids_system, IdsSystem)


def test_cids_polymorphic_identity(cids_system):
    assert cids_system.type == "CIDS"
    assert isinstance(cids_system, CidsSystem)
    assert isinstance(cids_system, IdsSystem)


# ==================== get_ids_system_model ====================


def test_get_ids_system_model_nids():
    assert get_ids_system_model("NIDS") is NidsSystem


def test_get_ids_system_model_hids():
    assert get_ids_system_model("HIDS") is HidsSystem


def test_get_ids_system_model_cids():
    assert get_ids_system_model("CIDS") is CidsSystem


def test_get_ids_system_model_case_insensitive():
    assert get_ids_system_model("nids") is NidsSystem
    assert get_ids_system_model("hIds") is HidsSystem
    assert get_ids_system_model("Cids") is CidsSystem


def test_get_ids_system_model_unknown_type():
    result = get_ids_system_model("UNKNOWN")
    assert result is IdsSystem


def test_get_ids_system_model_none():
    result = get_ids_system_model(None)
    assert result is IdsSystem


def test_get_ids_system_model_empty_string():
    result = get_ids_system_model("")
    assert result is IdsSystem


# ==================== IDS CONTAINER HTTP URL ====================


def test_ids_system_get_container_http_url_with_sensor_component(mock_host_system):
    """Base IdsSystem should prefer SENSOR component port when components exist."""
    sensor = IdsComponent(id=20, ids_id=10, name="sensor", role="SENSOR", port=9090)

    ids = IdsSystem(
        id=10,
        name="Test-IDS",
        port=8080,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        host_system=mock_host_system,
    )
    ids.components = [sensor]

    with patch("app.models.ids_system.get_core_host_ip", return_value="172.17.0.1"):
        url = ids.get_container_http_url()
        assert url == "http://172.17.0.1:9090"


def test_ids_system_get_container_http_url_no_sensor_component(mock_host_system):
    """Base IdsSystem should use its own port when no SENSOR component exists."""
    aggregator = IdsComponent(
        id=21, ids_id=10, name="aggregator", role="AGGREGATOR", port=9091
    )

    ids = IdsSystem(
        id=10,
        name="Test-IDS",
        port=8080,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        host_system=mock_host_system,
    )
    ids.components = [aggregator]

    with patch("app.models.ids_system.get_core_host_ip", return_value="172.17.0.1"):
        url = ids.get_container_http_url()
        assert url == "http://172.17.0.1:8080"


def test_ids_system_get_container_http_url_remote_host(mock_remote_host):
    """When host is remote (not Core/localhost), should use host's address."""
    ids = IdsSystem(
        id=10,
        name="Test-IDS",
        port=8080,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        host_system=mock_remote_host,
    )
    ids.components = []

    url = ids.get_container_http_url()
    assert url == "http://192.168.5.10:8080"


@pytest.mark.asyncio
async def test_cids_update_attributes_redeploys_only_changed_service(mock_host_system):
    sensor_1 = IdsComponent(
        id=31,
        ids_id=5,
        name="sensor-1",
        service_name="sensor",
        role="SENSOR",
        port=9090,
        host_system_id=mock_host_system.id,
        runtime_configuration_id=1,
        count=2,
    )
    sensor_2 = IdsComponent(
        id=32,
        ids_id=5,
        name="sensor-2",
        service_name="sensor",
        role="SENSOR",
        port=9091,
        host_system_id=mock_host_system.id,
        runtime_configuration_id=1,
        count=2,
    )
    aggregator = IdsComponent(
        id=33,
        ids_id=5,
        name="aggregator-1",
        service_name="aggregator",
        role="AGGREGATOR",
        port=9092,
        host_system_id=mock_host_system.id,
        runtime_configuration_id=None,
        count=1,
    )
    cids = CidsSystem(
        id=5,
        name="CIDS-test",
        port=8080,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        description="Test CIDS",
        configuration_id=1,
        ids_tool_id=3,
        host_system_id=mock_host_system.id,
        host_system=mock_host_system,
        type="CIDS",
    )
    cids.components = [sensor_1, sensor_2, aggregator]

    update = IdsContainerUpdate(
        id=5,
        description="updated",
        configuration_id=1,
        components=[
            {
                "id": sensor_1.id,
                "runtime_configuration_id": 7,
                "count": 3,
            }
        ],
    )

    with patch(
        "app.deployment.update_ids_components",
        new_callable=AsyncMock,
    ) as mock_update_ids_components:
        await cids.update_attributes(AsyncMock(), update)

    assert sensor_1.runtime_configuration_id == 7
    assert sensor_2.runtime_configuration_id == 7
    assert sensor_1.count == 3
    assert sensor_2.count == 3
    assert aggregator.runtime_configuration_id is None
    assert aggregator.count == 1
    changed_services = mock_update_ids_components.await_args.args[2]
    assert len(changed_services) == 1
    assert changed_services[0].service_name == "sensor"
    assert changed_services[0].count == 3
    assert changed_services[0].runtime_configuration_id == 7


# ==================== CIDS get_container_http_url ====================


def test_cids_get_container_http_url_sensor_with_host_system(cids_system):
    """CIDS should route to sensor's own URL when sensor has its own host_system."""
    sensor = cids_system.components[1]  # The SENSOR component
    sensor_host = DockerHostSystem(
        id=5, name="Sensor Host", host="10.0.0.50", docker_port=2375
    )
    sensor.host_system = sensor_host

    with patch("app.models.ids_component.get_core_host_ip", return_value="172.17.0.1"):
        url = cids_system.get_container_http_url()
        # Sensor has its own host_system, so should use its get_http_url()
        assert "9090" in url


def test_cids_get_container_http_url_sensor_no_host_system_core(cids_system):
    """CIDS with sensor (no host_system) on Core host should use core IP."""
    sensor = cids_system.components[1]
    sensor.host_system = None

    with patch("app.models.ids_system.get_core_host_ip", return_value="172.17.0.1"):
        url = cids_system.get_container_http_url()
        assert url == "http://172.17.0.1:9090"


def test_cids_get_container_http_url_sensor_no_host_system_remote(
    cids_system, mock_remote_host
):
    """CIDS with sensor (no host_system) on remote host should use remote host address."""
    cids_system.host_system = mock_remote_host
    sensor = cids_system.components[1]
    sensor.host_system = None

    url = cids_system.get_container_http_url()
    assert url == "http://192.168.5.10:9090"


def test_cids_get_container_http_url_no_components(mock_host_system):
    """CIDS without any components should fallback to parent behavior."""
    cids = CidsSystem(
        id=5,
        name="Empty-CIDS",
        port=8082,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        host_system=mock_host_system,
    )
    cids.components = []

    with patch("app.models.ids_system.get_core_host_ip", return_value="172.17.0.1"):
        url = cids.get_container_http_url()
        assert url == "http://172.17.0.1:8082"


def test_cids_get_container_http_url_no_sensor(mock_host_system):
    """CIDS with only non-sensor components should fallback to parent behavior."""
    aggregator = IdsComponent(
        id=30, ids_id=5, name="aggregator", role="AGGREGATOR", port=9091
    )

    cids = CidsSystem(
        id=5,
        name="NoSensor-CIDS",
        port=8082,
        status=STATUS.IDLE.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        host_system=mock_host_system,
    )
    cids.components = [aggregator]

    with patch("app.models.ids_system.get_core_host_ip", return_value="172.17.0.1"):
        url = cids.get_container_http_url()
        assert url == "http://172.17.0.1:8082"


# ==================== is_busy / is_available ====================


@pytest.mark.asyncio
async def test_is_busy_setting_up(nids_system):
    nids_system.status = STATUS.SETTING_UP.value
    assert await nids_system.is_busy() is False


@pytest.mark.asyncio
async def test_nids_is_busy(nids_system):
    nids_system.status = STATUS.ACTIVE.value
    assert await nids_system.is_busy() is True


@pytest.mark.asyncio
async def test_hids_is_busy(hids_system):
    hids_system.status = STATUS.ACTIVE.value
    assert await hids_system.is_busy() is True


# ==================== SUBCLASS ANALYSIS METHODS ====================


@pytest.mark.asyncio
async def test_nids_start_network_analysis(nids_system):
    with patch(
        "app.models.ids_system.start_network_analysis", new_callable=AsyncMock
    ) as mock_start:
        mock_start.return_value = MagicMock(status_code=200)
        result = await nids_system.start_network_analysis({"key": "value"})
        mock_start.assert_awaited_once()
        assert result.status_code == 200


@pytest.mark.asyncio
async def test_nids_start_static_analysis(nids_system):
    with patch(
        "app.models.ids_system.start_static_analysis", new_callable=AsyncMock
    ) as mock_start:
        mock_start.return_value = MagicMock(status_code=200)
        result = await nids_system.start_static_analysis({}, MagicMock())
        mock_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_hids_start_static_analysis(hids_system):
    with patch(
        "app.models.ids_system.start_static_analysis", new_callable=AsyncMock
    ) as mock_start:
        mock_start.return_value = MagicMock(status_code=200)
        result = await hids_system.start_static_analysis({}, MagicMock())
        mock_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_hids_start_network_analysis(hids_system):
    with patch(
        "app.models.ids_system.start_network_analysis", new_callable=AsyncMock
    ) as mock_start:
        mock_start.return_value = MagicMock(status_code=200)
        result = await hids_system.start_network_analysis({"key": "value"})
        mock_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_cids_start_network_analysis(cids_system):
    with patch(
        "app.models.ids_system.start_network_analysis", new_callable=AsyncMock
    ) as mock_start:
        mock_start.return_value = MagicMock(status_code=200)
        result = await cids_system.start_network_analysis({"key": "value"})
        mock_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_cids_start_static_analysis(cids_system):
    with patch(
        "app.models.ids_system.start_static_analysis", new_callable=AsyncMock
    ) as mock_start:
        mock_start.return_value = MagicMock(status_code=200)
        result = await cids_system.start_static_analysis({}, MagicMock())
        mock_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_analysis(nids_system):
    with patch(
        "app.models.ids_system.stop_analysis", new_callable=AsyncMock
    ) as mock_stop:
        mock_stop.return_value = MagicMock(status_code=200)
        result = await nids_system.stop_analysis()
        mock_stop.assert_awaited_once()
        assert result.status_code == 200


# ==================== QUERY FUNCTIONS ====================


@pytest.mark.asyncio
async def test_get_ids_system_by_id(db_session_fixture: DatabaseSessionFixture):
    db = await db_session_fixture.get_db_session()
    result = await get_ids_system_by_id(db, 1)
    assert result is not None


@pytest.mark.asyncio
async def test_get_ids_system_by_id_not_found():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await get_ids_system_by_id(mock_db, 999)
    assert result is None


@pytest.mark.asyncio
async def test_get_all_container(db_session_fixture: DatabaseSessionFixture):
    db = await db_session_fixture.get_db_session()
    result = await get_all_container(db)
    assert isinstance(result, list)
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_remove_container_by_id_existing(
    db_session_fixture: DatabaseSessionFixture,
):
    db = await db_session_fixture.get_db_session()
    container = await db_session_fixture.get_ids_container_model()
    await remove_container_by_id(db, 1)
    assert container.deployment_status == DEPLOYMENT_STATUS.DELETED.value
    assert container.status == STATUS.IDLE.value
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_remove_container_by_id_nonexistent():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    await remove_container_by_id(mock_db, 999)
    mock_db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_ids_status():
    mock_db = AsyncMock()
    container = MagicMock(spec=IdsSystem)
    container.status = STATUS.IDLE.value

    await update_ids_status(mock_db, STATUS.ACTIVE.value, container)
    assert container.status == STATUS.ACTIVE.value
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(container)
