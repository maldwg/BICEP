import pytest
from app.test.fixtures import *
from app.models.dataset_types_implementation.network_traffic_data import *
from app.models.dataset_types import *
from app.utils import Precision, SecondPrecision, MilisecondPrecision, MinutePrecision, HourPrecision
import io
from types import SimpleNamespace

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
    assert (TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS) == (22, 6, 893, 78, 0, 15)


@pytest.mark.asyncio
async def test_get_precision(mock_network_traffic_data_dataset_type, sample_dataset):
    labels_file_path = sample_dataset.labels_file_path
    precision = await mock_network_traffic_data_dataset_type.calculate_precision(labels_file_path)
    print(type(precision))
    assert isinstance(precision, MinutePrecision)


def test_multiclass_counts_and_detection_coverage(tmp_path):
    labels_file = tmp_path / "multiclass.csv"
    labels_file.write_text(
        "Label,Timestamp,Source IP,Source Port,Destination IP,Destination Port\n"
        "benign,2026-01-01T00:00:00,10.0.0.1,1000,10.0.0.2,80\n"
        "scan,2026-01-01T00:00:01,10.0.0.3,1001,10.0.0.4,443\n"
        "botnet,2026-01-01T00:00:02,10.0.0.5,1002,10.0.0.6,53\n",
        encoding="utf-8",
    )
    dataset = SimpleNamespace(
        labels_file_path=str(labels_file), timestamp_precision="second"
    )
    alerts = [
        Alert(
            "2026-01-01T00:00:01",
            "10.0.0.3",
            "1001",
            "10.0.0.4",
            "443",
            1,
        )
    ]

    assert network_traffic_data_get_class_counts(str(labels_file)) == {
        "benign": 1,
        "botnet": 1,
        "scan": 1,
    }
    result = network_traffic_data_get_class_detection_statistics(dataset, alerts)

    by_class = {row["class_label"]: row for row in result["classes"]}
    assert by_class["scan"] == {
        "class_label": "scan",
        "support": 1,
        "detected": 1,
        "missed": 0,
        "detection_rate": 1.0,
    }
    assert by_class["benign"]["detection_rate"] == 0.0
    assert by_class["botnet"]["detection_rate"] == 0.0
    assert result["unassigned_alerts"] == 0
