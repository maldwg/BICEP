import pytest
from datetime import datetime
from app.metrics import calculate_evaluation_metrics, get_positves_and_negatives_from_dataset, get_column_ids, get_item_counts_of_dict
from app.utils import calculate_benign_and_malicious_ammount
from app.models.dataset import Dataset
from app.bicep_utils.models.ids_base import Alert


TESTS_BASE_DIR = "./backend/core/app/test"


@pytest.fixture
def sample_dataset():
    return Dataset(
        name="TestDataset",
        description="Test dataset for IDS evaluation",
        pcap_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.pcap",
        labels_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.csv",
        ammount_benign=899,
        ammount_malicious=100
    )

@pytest.fixture
def sample_alerts():
    alerts = [
        Alert("07/07/2017 09:00:00", "192.168.10.5", "54108", "192.168.10.3", "389", 17),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "51905", "192.168.10.3", "389", 17),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49173", "192.168.10.3", "389", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49165", "192.168.10.3", "389", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49163", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49162", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49161", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49160", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49169", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.3", "88", "192.168.10.5", "49168", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49166", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.3", "88", "192.168.10.5", "49175", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49174", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49172", "192.168.10.3", "88", 6),
        Alert("07/07/2017 09:00:00", "192.168.10.5", "49170", "192.168.10.3", "88", 6)
    ]
    return alerts

@pytest.mark.asyncio
async def test_calculate_evaluation_metrics(sample_dataset, sample_alerts):
    # Simulate calculated metrics using utility functions
    benign_count, malicious_count = await calculate_benign_and_malicious_ammount(b"label,benign\n1,malicious")
    
    # Replace with actual metrics calculation logic
    metrics = await calculate_evaluation_metrics(sample_dataset, sample_alerts)
    correct_metrics = {
        "FPR": 0.01,
        "FNR": 0.91,
        "DR": 0.09,
        "FDR": 0.4,
        "ACCURACY": 0.9,
        "PRECISION": 0.6,
        "F_SCORE": 0.16,
        "UNASSIGNED_ALERTS_RATIO": 0.0
    }
    
    assert metrics == correct_metrics

@pytest.mark.asyncio
async def test_get_positives_and_negatives_from_dataset(sample_dataset, sample_alerts):
    TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS = await get_positves_and_negatives_from_dataset(sample_dataset, sample_alerts)
    assert (TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS) == (9,6,893,91,0,15)

# Test for get_column_ids
@pytest.mark.asyncio
async def test_get_column_ids():
    header = ["Time", "Source IP", "Source Port", "Destination", "Destination Port", "Label"]
    result_related_headers = await get_column_ids(header)

    expected_related_headers = (
        5,  # Label column
        0,  # Timestamp column
        1,  # Source IP column
        2,  # Source Port column
        3,  # Destination IP column
        4   # Destination Port column
    )

    header = ["Unknown", "Unrelated", "Time"]
    result_unrelated_headers = await get_column_ids(header)

    expected_unrelated_headers = (
        None,  # Label column
        2,     # Timestamp column
        None,  # Source IP column
        None,  # Source Port column
        None,  # Destination IP column
        None   # Destination Port column
    )
    assert (expected_related_headers, expected_unrelated_headers) == (result_related_headers, result_unrelated_headers)

@pytest.mark.asyncio
async def test_get_item_counts_of_dict():
    test_dict = {
        "a": [1, 2, 3],
        "b": [4, 5],
        "c": []
    }
    result_five_element_dict = await get_item_counts_of_dict(test_dict)

    empty_dict = {}
    result_empty_dict = await get_item_counts_of_dict(empty_dict)

    single_item_dict = {"a": [1]}
    result_single_dict = await get_item_counts_of_dict(single_item_dict)

    assert (5, 1, 0) == (result_five_element_dict, result_single_dict, result_empty_dict)