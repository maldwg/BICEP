import pytest
from docker import DockerClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.test.fixtures import *
from app.models.ensemble_techniques_implementation.majority_vote import majority_vote, combine_alerts_for_ids_in_alert_dict
from app.utils import normalize_and_parse_alert_timestamp


@pytest.mark.asyncio
async def test_execute_technique_by_name_on_alerts(mock_alerts):
    ensemble_technique = EnsembleTechnique(
        id=1,
        name="Majority Vote",
        description="Combines alerts based on majority voting.",
        function_name="majority_vote"
    )

    ensemble = MagicMock()
    ensemble.ensemble_ids = [1, 2, 3]
    unique_alert1 = mock_alerts[0]
    unique_alert2 = mock_alerts[1]
    common_alert = mock_alerts[2]
    mock_alerts_dict = {
        "container1": [unique_alert1, common_alert],
        "container2": [unique_alert2, common_alert]
    }
    ensembled_alerts = await ensemble_technique.execute_technique_by_name_on_alerts(mock_alerts_dict, ensemble)
    assert ensembled_alerts == [common_alert]


@pytest.mark.asyncio
async def test_majority_vote(mock_alerts,db_session_fixture: DatabaseSessionFixture):
    ensemble = await db_session_fixture.get_ensemble_model()
    container1 = MagicMock()
    container2 = MagicMock()
    ensemble.ensemble_ids = [container1, container2]

    common_alert: Alert = mock_alerts[0]

    alerts_dict = {
        "container1": mock_alerts,
        "container2": [common_alert]

    }

    majority_voted_alerts = await majority_vote(alerts_dict=alerts_dict, ensemble=ensemble)

    print(majority_voted_alerts)
    assert majority_voted_alerts == [common_alert]





@pytest.mark.asyncio
async def test_combine_alerts_for_ids_in_alert_dict(mock_alerts):
    first_alert: Alert = mock_alerts[0]
    second_alert: Alert = mock_alerts[1]
    third_alert: Alert = mock_alerts[2]
    fourth_alert: Alert = mock_alerts[3]

    alerts_dict = {
        "container1": mock_alerts,
        "container2": [first_alert]

    }
    common_alerts = {
        (normalize_and_parse_alert_timestamp(first_alert.time), first_alert.source_ip, first_alert.source_port, first_alert.destination_ip, first_alert.destination_port): {"container1": [first_alert], "container2": [first_alert]},
        (normalize_and_parse_alert_timestamp(second_alert.time), second_alert.source_ip, second_alert.source_port, second_alert.destination_ip, second_alert.destination_port): {"container1": [second_alert]},
        (normalize_and_parse_alert_timestamp(third_alert.time), third_alert.source_ip, third_alert.source_port, third_alert.destination_ip, third_alert.destination_port): {"container1": [third_alert, fourth_alert]}                                                                                                                                                                                                                            
    }

    common_alerts_format = await combine_alerts_for_ids_in_alert_dict(alerts_dict=alerts_dict)
    assert common_alerts_format == common_alerts


