import pytest
from docker import DockerClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.test.fixtures import *
from app.models.ensemble_technique import *



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
    ensemble = db_session_fixture.get_ensemble_model()
    container1 = MagicMock()
    container2 = MagicMock()
    ensemble.ensemble_ids = [container1, container2]
    common_alert: Alert = mock_alerts[0]
    other_alert: Alert = mock_alerts[1]
    unagreed_alert: Alert = mock_alerts[2]
    common_alerts = {
        f"{common_alert.time}-{common_alert.source_ip}-{common_alert.source_port}-{common_alert.destination_ip}-{common_alert.destination_port}": {"container1": [common_alert, other_alert], "container2": [common_alert]},
        f"{unagreed_alert.time}-{unagreed_alert.source_ip}-{unagreed_alert.source_port}-{unagreed_alert.destination_ip}-{unagreed_alert.destination_port}": {"container1": [unagreed_alert]}                                                                                                                                                                                                                            
    }
    majority_voted_alerts = await majority_vote(common_alerts=common_alerts, ensemble=ensemble)

    print(majority_voted_alerts)
    assert majority_voted_alerts == [common_alert]



