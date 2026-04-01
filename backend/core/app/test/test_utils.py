from unittest.mock import MagicMock, patch
import os
from pathlib import Path
import shutil
import pytest
from app.utils import *
from app.bicep_utils.models.ids_base import Alert
from app.test.fixtures import *

TESTS_BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = '/tmp/test_datasets'


@pytest.fixture(scope="module", autouse=True)
def setup_module():
    os.environ["DATASET_BASE_PATH"] = "/tmp"
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)
    yield
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)


@pytest.mark.asyncio
async def test_create_response_message():
    message = "Test message"
    status_code = 200
    response = create_response_message(message, status_code)
    assert response.status_code == 200
    assert response.body.decode() == '{ "message": "Test message" }'


@pytest.mark.asyncio
async def test_create_response_error():
    message = "Test error message"
    status_code = 500
    response = create_response_error(message, status_code)
    assert response.status_code == 500
    assert response.body.decode() == '{ "error": "Test error message" }'


@pytest.mark.asyncio
async def test_start_static_analysis():
    container = MagicMock()
    container.get_container_http_url.return_value = "http://test-container"
    form_data = {"key": "value"}
    dataset = MagicMock()
    dataset.data_file_path = "path/to/pcap"

    with patch('asyncio.create_task') as mock_create_task:
        response = await start_static_analysis(container, form_data, dataset)
        assert response.status_code == 200
        assert response.body.decode() == '{"message":"Successfully sending data in the background"}'

@pytest.mark.asyncio
async def test_calculate_and_add_dataset(db_session_fixture: DatabaseSessionFixture):
    db_session = await db_session_fixture.get_db_session()
    dataset_type = await db_session_fixture.get_dataset_type_model()
    labels_file_path = f'{TESTS_BASE_DIR}/testfiles/sample_data.csv'
    data_file_path = f'{TESTS_BASE_DIR}/testfiles/sample_data.pcap'

    name = "sample_data"
    description = "Test dataset"
    dataset_storage_location = f"{TEST_DIR}/{name}"
    os.makedirs(dataset_storage_location, 777, exist_ok=True)
    try:
        await calculate_and_add_dataset(data_file_path=data_file_path, labels_file_path=labels_file_path, name=name, description=description, dataset_type=dataset_type, db=db_session )
    finally:
        shutil.rmtree(dataset_storage_location)


@pytest.mark.asyncio
async def test_save_file_to_disk():
    file_content = b"mock file content"
    path = f"{TEST_DIR}/test_file.txt"
    await save_file_to_disk(file_content, path)

    with open(path, "rb") as f:
        saved_content = f.read()
        assert saved_content == file_content

    os.remove(path)




# TODO: find a way to test appropriately and test metrics.py alongside
# @pytest.mark.asyncio
# async def test_calculate_evaluation_metrics_and_push():
#     dataset = MagicMock()
#     alerts = MagicMock()  
#     container_name = "test_container"

#     with patch('app.prometheus.push_evaluation_metrics_to_prometheus') as mock_push_metrics: 
#         await calculate_evaluation_metrics_and_push(dataset, alerts, container_name)
#         mock_push_metrics.assert_called_once()


@pytest.mark.asyncio
async def test_extract_ts_srcip_srcport_dstip_dstport_from_alert():
    alert = Alert(
        destination_ip="192.168.0.2",
        destination_port= "80",
        source_ip="192.168.0.1",
        source_port="1234",
        time="2025-01-01T00:00:00Z",
        severity="0",
        type="Malware",
        message="Test malware injected" 
    )

    timestamp, source_ip, source_port, destination_ip, destination_port = extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)

    assert timestamp == "2025-01-01T00:00:00"
    assert source_ip == "192.168.0.1"
    assert source_port == "1234"
    assert destination_ip == "192.168.0.2"
    assert destination_port == "80"


@pytest.mark.asyncio
async def test_normalize_and_parse_alert_timestamp_miliseconds():
    timestamp = "2025-01-01T00:00:00.0000"
    normalized_timestamp = normalize_and_parse_alert_timestamp(timestamp, precision=MilisecondPrecision())
    assert normalized_timestamp == "2025-01-01T00:00:00" 

@pytest.mark.asyncio
async def test_normalize_and_parse_alert_timestamp_seconds():
    timestamp = "2025-01-01T00:02:02Z"
    normalized_timestamp = normalize_and_parse_alert_timestamp(timestamp, precision=SecondPrecision())
    assert normalized_timestamp == "2025-01-01T00:02:02" 

@pytest.mark.asyncio
async def test_normalize_and_parse_alert_timestamp_minutes():
    timestamp = "2025-01-01T11:00:00.123425Z"
    normalized_timestamp = normalize_and_parse_alert_timestamp(timestamp, precision=MinutePrecision())
    assert normalized_timestamp == "2025-01-01T11:00" 

@pytest.mark.asyncio
async def test_normalize_and_parse_alert_timestamp_hours():
    timestamp = "2025-01-01T10:00:23Z"
    normalized_timestamp = normalize_and_parse_alert_timestamp(timestamp, precision=HourPrecision())
    assert normalized_timestamp == "2025-01-01T10:00" 

@pytest.mark.asyncio
async def test_get_item_counts_of_dict():
    test_dict = {
        "a": [1, 2, 3],
        "b": [4, 5],
        "c": []
    }
    result_five_element_dict = get_item_counts_of_dict(test_dict)

    empty_dict = {}
    result_empty_dict = get_item_counts_of_dict(empty_dict)

    single_item_dict = {"a": [1]}
    result_single_dict = get_item_counts_of_dict(single_item_dict)

    assert (5, 1, 0) == (result_five_element_dict, result_single_dict, result_empty_dict)


def test_check_directory_is_empty_with_empty_dir():
    path = "/tmp/testing-temporary-empty-dir"
    os.mkdir(path)
    is_directory_empty = directory_is_empty(path)
    assert is_directory_empty == True
    shutil.rmtree(path)

def test_check_directory_is_empty_with_filled_dir():
    path = "/tmp/testing-temporary-empty-dir"
    os.mkdir(path)
    open(path+"/test-file.txt", "a").close()
    is_directory_empty = directory_is_empty(path)
    assert is_directory_empty == False
    shutil.rmtree(path)


# ==================== file_type_is_accepted ====================


def test_file_type_is_accepted_config_lua():
    assert file_type_is_accepted(FILE_TYPES.CONFIG.value, "lua") is True


def test_file_type_is_accepted_config_yaml():
    assert file_type_is_accepted(FILE_TYPES.CONFIG.value, "yaml") is True


def test_file_type_is_accepted_config_xml():
    assert file_type_is_accepted(FILE_TYPES.CONFIG.value, "xml") is True


def test_file_type_is_accepted_config_conf():
    assert file_type_is_accepted(FILE_TYPES.CONFIG.value, "conf") is True


def test_file_type_is_accepted_config_invalid():
    assert file_type_is_accepted(FILE_TYPES.CONFIG.value, "txt") is False


def test_file_type_is_accepted_test_data_pcap():
    assert file_type_is_accepted(FILE_TYPES.TEST_DATA.value, "pcap") is True


def test_file_type_is_accepted_test_data_csv():
    assert file_type_is_accepted(FILE_TYPES.TEST_DATA.value, "csv") is True


def test_file_type_is_accepted_test_data_invalid():
    assert file_type_is_accepted(FILE_TYPES.TEST_DATA.value, "json") is False


def test_file_type_is_accepted_ruleset_rules():
    assert file_type_is_accepted(FILE_TYPES.RULE_SET.value, "rules") is True


def test_file_type_is_accepted_ruleset_invalid():
    assert file_type_is_accepted(FILE_TYPES.RULE_SET.value, "txt") is False


def test_file_type_is_accepted_unknown_type():
    assert file_type_is_accepted("unknown-type", "txt") is False


# ==================== find_free_port ====================


def test_find_free_port():
    port = find_free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535


def test_find_free_port_returns_different_ports():
    port1 = find_free_port()
    port2 = find_free_port()
    # Ports may or may not be different, but both should be valid
    assert isinstance(port1, int)
    assert isinstance(port2, int)


# ==================== get_core_url ====================


def test_get_core_url():
    with patch("app.utils.get_core_host_ip", return_value="172.17.0.1"):
        with patch.dict(os.environ, {"EXTERNAL_FASTAPI_PORT": "8000"}):
            url = get_core_url()
            assert url == "http://172.17.0.1:8000"


# ==================== create_generic_response_message_for_ensemble ====================


def test_create_generic_response_message_for_ensemble():
    result = create_generic_response_message_for_ensemble("Test message", 200)
    assert result == {"content": "Test message", "status_code": 200}


def test_create_generic_response_message_for_ensemble_error():
    result = create_generic_response_message_for_ensemble("Error occurred", 500)
    assert result == {"content": "Error occurred", "status_code": 500}


# ==================== parse_response_for_triggered_analysis ====================


@pytest.mark.asyncio
async def test_parse_response_for_triggered_analysis_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_container = MagicMock()
    mock_container.id = 1

    result = await parse_response_for_triggered_analysis(
        mock_response, mock_container, "static"
    )
    assert result.status_code == 200
    assert b"analysis triggered" in result.body


@pytest.mark.asyncio
async def test_parse_response_for_triggered_analysis_failure():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_container = MagicMock()
    mock_container.id = 1

    result = await parse_response_for_triggered_analysis(
        mock_response, mock_container, "static"
    )
    assert result.status_code == 500
    assert b"could not be triggered" in result.body


@pytest.mark.asyncio
async def test_parse_response_for_triggered_analysis_success_with_ensemble():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_container = MagicMock()
    mock_container.id = 1

    result = await parse_response_for_triggered_analysis(
        mock_response, mock_container, "network", ensemble_id=5
    )
    assert result.status_code == 200
    assert b"for ensemble 5" in result.body
    assert b"triggered" in result.body


@pytest.mark.asyncio
async def test_parse_response_for_triggered_analysis_failure_with_ensemble():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_container = MagicMock()
    mock_container.id = 2

    result = await parse_response_for_triggered_analysis(
        mock_response, mock_container, "network", ensemble_id=3
    )
    assert result.status_code == 500
    assert b"for ensemble 3" in result.body
    assert b"could not be triggered" in result.body


# ==================== remove_directory ====================


@pytest.mark.asyncio
async def test_remove_directory_existing():
    path = "/tmp/test-remove-dir-utils"
    os.makedirs(path, exist_ok=True)
    open(path + "/test-file.txt", "a").close()
    assert os.path.exists(path)

    await remove_directory(path)
    assert not os.path.exists(path)


@pytest.mark.asyncio
async def test_remove_directory_nonexistent():
    """Should not raise when directory doesn't exist (exception is logged)."""
    path = "/tmp/test-nonexistent-dir-to-remove"
    # Should not raise
    await remove_directory(path)


# ==================== create_directory ====================


@pytest.mark.asyncio
async def test_create_directory_new():
    path = "/tmp/test-create-new-dir-utils"
    if os.path.exists(path):
        shutil.rmtree(path)

    await create_directory(path)
    assert os.path.exists(path)
    shutil.rmtree(path)


@pytest.mark.asyncio
async def test_create_directory_existing():
    """Should not raise when directory already exists."""
    path = "/tmp/test-create-existing-dir-utils"
    os.makedirs(path, exist_ok=True)

    await create_directory(path)
    assert os.path.exists(path)
    shutil.rmtree(path)


# ==================== get_length_of_nested_dict ====================


def test_get_length_of_nested_dict():
    nested = {
        "key1": {"container1": [1, 2, 3], "container2": [4, 5]},
        "key2": {"container3": [6]},
    }
    assert get_length_of_nested_dict(nested) == 6


def test_get_length_of_nested_dict_empty():
    assert get_length_of_nested_dict({}) == 0


def test_get_length_of_nested_dict_empty_inner():
    nested = {"key1": {"container1": []}}
    assert get_length_of_nested_dict(nested) == 0


# ==================== directory_is_empty - edge cases ====================


def test_directory_is_empty_nonexistent_path():
    """Non-existent path should return True."""
    assert directory_is_empty("/tmp/this-path-does-not-exist-12345") is True


# ==================== get_precision_by_name ====================


def test_get_precision_by_name_hour():
    p = get_precision_by_name("hour")
    assert isinstance(p, HourPrecision)


def test_get_precision_by_name_minute():
    p = get_precision_by_name("minute")
    assert isinstance(p, MinutePrecision)


def test_get_precision_by_name_second():
    p = get_precision_by_name("second")
    assert isinstance(p, SecondPrecision)


def test_get_precision_by_name_milisecond():
    p = get_precision_by_name("milisecond")
    assert isinstance(p, MilisecondPrecision)


def test_get_precision_by_name_unknown():
    assert get_precision_by_name("nanosecond") is None


def test_get_precision_by_name_empty():
    assert get_precision_by_name("") is None


# ==================== Precision classes - tolerance calculations ====================


def test_hour_precision_tolerance():
    from datetime import datetime
    p = HourPrecision()
    ts = datetime(2025, 1, 1, 12, 30, 45)
    results = p.calculate_timestamps_with_tolerance(ts, tolerance_unit=1)
    assert len(results) == 3
    # Should be 12:29, 12:30, 12:31 (seconds and microseconds zeroed)
    assert results[0].minute == 29
    assert results[1].minute == 30
    assert results[2].minute == 31


def test_minute_precision_tolerance():
    from datetime import datetime
    p = MinutePrecision()
    ts = datetime(2025, 1, 1, 12, 30, 45)
    results = p.calculate_timestamps_with_tolerance(ts, tolerance_unit=2)
    assert len(results) == 5
    # Should span 12:28 to 12:32
    assert results[0].minute == 28
    assert results[4].minute == 32


def test_second_precision_tolerance():
    from datetime import datetime
    p = SecondPrecision()
    ts = datetime(2025, 1, 1, 12, 30, 45, 500000)
    results = p.calculate_timestamps_with_tolerance(ts, tolerance_unit=1)
    assert len(results) == 3
    assert results[0].second == 44
    assert results[1].second == 45
    assert results[2].second == 46


def test_milisecond_precision_tolerance():
    from datetime import datetime
    p = MilisecondPrecision()
    ts = datetime(2025, 1, 1, 12, 30, 45, 500000)
    results = p.calculate_timestamps_with_tolerance(ts, tolerance_unit=1)
    assert len(results) == 3
    # Milisecond precision downsamples to seconds
    assert results[0].second == 44
    assert results[1].second == 45
    assert results[2].second == 46


# ==================== Precision classes - replace and format ====================


def test_hour_precision_trim_datetime_to_str():
    from datetime import datetime
    p = HourPrecision()
    ts = datetime(2025, 6, 15, 14, 35, 22, 123456)
    result = p.trim_datetime_timestamp_to_str(ts)
    assert result == "2025-06-15T14:35"


def test_minute_precision_trim_datetime_to_str():
    from datetime import datetime
    p = MinutePrecision()
    ts = datetime(2025, 6, 15, 14, 35, 22, 123456)
    result = p.trim_datetime_timestamp_to_str(ts)
    assert result == "2025-06-15T14:35"


def test_second_precision_trim_datetime_to_str():
    from datetime import datetime
    p = SecondPrecision()
    ts = datetime(2025, 6, 15, 14, 35, 22, 123456)
    result = p.trim_datetime_timestamp_to_str(ts)
    assert result == "2025-06-15T14:35:22"


def test_milisecond_precision_trim_datetime_to_str():
    from datetime import datetime
    p = MilisecondPrecision()
    ts = datetime(2025, 6, 15, 14, 35, 22, 123456)
    result = p.trim_datetime_timestamp_to_str(ts)
    assert result == "2025-06-15T14:35:22"


# ==================== STATUS / ANALYSIS_STATUS / FILE_TYPES / DOCKER_HOST_STATUS Enums ====================


def test_status_enum_values():
    assert STATUS.ACTIVE.value == "active"
    assert STATUS.IDLE.value == "idle"
    assert STATUS.SETTING_UP.value == "setting-up"


def test_analysis_status_enum_values():
    assert ANALYSIS_STATUS.LOGS_SENT.value == "LOGS_SENT"
    assert ANALYSIS_STATUS.PROCESSING.value == "PROCESSING"
    assert ANALYSIS_STATUS.IDLE.value == "IDLE"


def test_file_types_enum_values():
    assert FILE_TYPES.CONFIG.value == "configuration"
    assert FILE_TYPES.TEST_DATA.value == "test-data"
    assert FILE_TYPES.RULE_SET.value == "rule-set"


def test_docker_host_status_enum_values():
    assert DOCKER_HOST_STATUS.AVAILABLE.value == "available"
    assert DOCKER_HOST_STATUS.UNAVAILABLE.value == "unavailable"


# ==================== start_network_analysis ====================


@pytest.mark.asyncio
async def test_start_network_analysis():
    container = MagicMock()
    container.get_container_http_url.return_value = "http://test-container"
    data = {"interface": "eth0"}

    with patch("app.utils.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        response = await start_network_analysis(container, data)
        assert response.status_code == 200
        mock_client.post.assert_awaited_once()


# ==================== stop_analysis ====================


@pytest.mark.asyncio
async def test_stop_analysis():
    container = MagicMock()
    container.get_container_http_url.return_value = "http://test-container"

    with patch("app.utils.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        response = await stop_analysis(container)
        assert response.status_code == 200
        mock_client.post.assert_awaited_once()

