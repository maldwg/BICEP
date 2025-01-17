import io
import csv
from fastapi import Response
from fastapi.responses import JSONResponse
from unittest.mock import MagicMock, patch
import os
import shutil
import pytest
import asyncio
from app.utils import *
from app.models.dataset import Dataset, add_dataset
from app.prometheus import push_evaluation_metrics_to_prometheus

TEST_DIR = '/tmp/test_datasets'


@pytest.fixture(scope="module", autouse=True)
def setup_module():
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
    pcap_file = b"mock pcap content"
    labels_file = b"mock labels content"
    name = "dataset1"
    description = "Test dataset"
    db = MagicMock()

    dataset_storage_location = f"{TEST_DIR}/{name}"
    os.makedirs(dataset_storage_location, exist_ok=True)

    try:
        await calculate_and_add_dataset(pcap_file, labels_file, name, description, db)
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
async def test_calculate_malicious_benign_counts():
    labels_file = io.BytesIO(b"benign,malicious\nbenign,benign\nmalicious,malicious")
    benign_count, malicious_count = await calculate_malicious_benign_counts(labels_file)
    assert benign_count == 2
    assert malicious_count == 1


@pytest.mark.asyncio
async def test_calculate_evaluation_metrics_and_push():
    dataset = MagicMock()
    alerts = MagicMock()  
    container_name = "test_container"

    with patch('app.prometheus.push_evaluation_metrics_to_prometheus') as mock_push_metrics: 
        await calculate_evaluation_metrics_and_push(dataset, alerts, container_name)
        mock_push_metrics.assert_called_once()


@pytest.mark.asyncio
async def test_extract_ts_srcip_srcport_dstip_dstport_from_alert():
    alert = MagicMock()
    alert.source_ip = "192.168.0.1"
    alert.source_port = "1234"
    alert.destination_ip = "192.168.0.2"
    alert.destination_port = "80"
    alert.time = "2025-01-01T00:00:00Z" 

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


# Utility functions used in the tests
def create_response_message(message: str, status_code: int) -> Response:
    return Response(content=f'{{ "message": "{message}" }}', status_code=status_code)


def create_response_error(message: str, status_code: int) -> Response:
    return Response(content=f'{{ "error": "{message}" }}', status_code=status_code)


async def start_static_analysis(container, form_data, dataset):
    endpoint = "/analysis/static"
    container_url = container.get_container_http_url()
    async def send_request_in_background(): 
        try:
            async with httpx.AsyncClient() as client:  
                with open(dataset.pcap_file_path, "rb") as f:
                    form_data["dataset"] = (dataset.name, f, "application/octet-stream")
                    response = await client.post(container_url + endpoint, files=form_data, timeout=180)
                    response.raise_for_status()
        except Exception as e:
            print(e)
    task = asyncio.create_task(send_request_in_background())
    return JSONResponse(content={"message": "Successfully sending data in the background"}, status_code=200)


async def save_file_to_disk(file, path):
    with open(path, "wb") as f:
        f.write(file)


async def calculate_malicious_benign_counts(input_file):
    benign_count = 0
    malicious_count = 0
    header = True
    with input_file as input_csv:
        reader = csv.reader(input_csv)
        for row in reader:
            if header:
                header = False
                continue
            if any("benign" in cell.lower() for cell in row):
                benign_count += 1
            else:
                malicious_count += 1
    return benign_count, malicious_count
