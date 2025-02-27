import pytest
from datetime import datetime
from app.metrics import calculate_evaluation_metrics
from app.models.dataset import Dataset
from app.bicep_utils.models.ids_base import Alert
from .fixtures import *

TESTS_BASE_DIR = "./backend/core/app/test"


# @pytest.fixture
# def sample_dataset():
#     return Dataset(
#         name="TestDataset",
#         description="Test dataset for IDS evaluation",
#         data_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.pcap",
#         labels_file_path=f"{TESTS_BASE_DIR}/testfiles/sample_data.csv",
#         ammount_benign=899,
#         ammount_malicious=100,
#         dataset_type_id = 1,
#         dataset_type=
#     )

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
async def test_calculate_evaluation_metrics(sample_alerts, db_session_fixture: DatabaseSessionFixture):
    # Simulate calculated metrics using utility functions
    sample_dataset = await db_session_fixture.get_dataset_model()
    db = await db_session_fixture.get_db_session()
    print(sample_dataset.id)
    # Replace with actual metrics calculation logic
    metrics = await calculate_evaluation_metrics(db, sample_dataset.id, sample_alerts)
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

