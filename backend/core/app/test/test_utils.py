from unittest.mock import MagicMock, patch
import os
import shutil
import pytest
from app.utils import *
from app.bicep_utils.models.ids_base import Alert

TESTS_BASE_DIR = "./backend/core/app/test"
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
    dataset.pcap_file_path = "path/to/pcap"

    with patch('asyncio.create_task') as mock_create_task:
        response = await start_static_analysis(container, form_data, dataset)
        assert response.status_code == 200
        assert response.body.decode() == '{"message":"Successfully sending data in the background"}'

@pytest.mark.asyncio
async def test_calculate_and_add_dataset():
    labels_file_in_bytes = open(f'{TESTS_BASE_DIR}/testfiles/sample_data.csv', 'rb').read()
    pcap_file_in_bytes = open(f'{TESTS_BASE_DIR}/testfiles/sample_data.pcap', 'rb').read()

    name = "sample_data"
    description = "Test dataset"
    db = MagicMock()

    dataset_storage_location = f"{TEST_DIR}/{name}"
    os.makedirs(dataset_storage_location, 777, exist_ok=True)

    try:
        await calculate_and_add_dataset(pcap_file_in_bytes, labels_file_in_bytes, name, description, db)
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


@pytest.mark.asyncio
async def test_calculate_malicious_benign_counts_from_text_stream():
    labels_file_path = open(f'{TESTS_BASE_DIR}/testfiles/sample_data.csv', 'r')
    benign_count, malicious_count = await calculate_malicious_benign_counts_from_text_stream(labels_file_path)
    assert (benign_count, malicious_count) == (899,100)

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

    timestamp, source_ip, source_port, destination_ip, destination_port = await extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)

    assert timestamp == "2025-01-01T00:00"
    assert source_ip == "192.168.0.1"
    assert source_port == "1234"
    assert destination_ip == "192.168.0.2"
    assert destination_port == "80"


@pytest.mark.asyncio
async def test_normalize_and_parse_alert_timestamp():
    timestamp = "2025-01-01T00:00:00Z"
    normalized_timestamp = await normalize_and_parse_alert_timestamp(timestamp)
    assert normalized_timestamp == "2025-01-01T00:00" 