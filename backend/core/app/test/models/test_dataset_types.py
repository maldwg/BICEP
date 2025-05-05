import pytest
from app.test.fixtures import *
from app.models.dataset_types_implementation.network_traffic_data import *
from app.models.dataset_types import *
from app.utils import Precision, SecondPrecision, MilisecondPrecision, MinutePrecision, HourPrecision
import io

@pytest.fixture
def sample_dataset():
    return Dataset(
        name="TestDataset",
        description="Test dataset for IDS evaluation",
        data_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.pcap",
        labels_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.csv",
        ammount_benign=899,
        ammount_malicious=100,
        dataset_type_id = 1,
        timestamp_precision="minute"
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

@pytest.fixture
def mock_network_traffic_data_dataset_type():
    return DatasetType(
        id = 1,
        name = "network_traffic_data",
        description = "Description",
        function_prefix = "network_traffic_data"
    )

@pytest.mark.asyncio
async def test_calculate_malicious_benign_counts(mock_network_traffic_data_dataset_type, sample_dataset):
    labels_file_path = sample_dataset.labels_file_path
    benign_count, malicious_count = await mock_network_traffic_data_dataset_type.get_benign_and_malicious_counts(labels_file_path)
    assert (benign_count, malicious_count) == (899,100)

@pytest.mark.asyncio
async def test_get_positives_and_negatives_from_dataset(mock_network_traffic_data_dataset_type, sample_dataset, sample_alerts):
    TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS = await mock_network_traffic_data_dataset_type.get_positives_and_negatives_from_dataset(sample_dataset, sample_alerts)
    assert (TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS) == (9,6,893,91,0,15)


@pytest.mark.asyncio
async def test_get_precision(mock_network_traffic_data_dataset_type, sample_dataset):
    labels_file_path = sample_dataset.labels_file_path
    precision = await mock_network_traffic_data_dataset_type.calculate_precision(labels_file_path)
    print(type(precision))
    assert isinstance(precision, MinutePrecision)

