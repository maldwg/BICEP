import asyncio
from http.client import HTTPResponse
import json

from app.metrics import calculate_evaluation_metrics
from app.bicep_utils.models.ids_base import Alert
from app.models.ensemble_ids import (
    get_all_ensemble_container,
    EnsembleIds,
    get_ensemble_ids_by_ids,
    update_sendig_logs_status,
    last_container_sending_logs,
)
from app.models.configuration import Configuration, get_config_by_id
from app.models.ids_system import (
    IdsSystem,
    get_ids_system_by_id,
    update_ids_status,
)
from app.models.ensemble_technique import (
    EnsembleTechnique,
    get_ensemble_technique_by_id,
)
from fastapi import APIRouter, Depends, Response, BackgroundTasks
from fastapi.encoders import jsonable_encoder
import uuid
from app.validation.models import (
    AlertData,
    EnsembleCreate,
    NetworkAnalysisData,
    StaticAnalysisData,
    stop_analysisData,
    AnalysisFinishedData,
)
from app.models.ensemble import (
    get_all_ensembles,
    Ensemble,
    add_ensemble,
    get_ensemble_by_id,
    remove_ensemble,
    update_ensemble_status,
)
from app.models.ids_system import IdsSystem
from app.models.dataset import Dataset, get_dataset_by_id
import httpx
from app.utils import (
    calculate_evaluation_metrics_and_push,
    deregister_container_from_ensemble,
    find_free_port,
    STATUS,
    ANALYSIS_STATUS,
    create_response_error,
    create_response_message,
    create_generic_response_message_for_ensemble,
)
from fastapi.responses import JSONResponse
from app.loki import (
    push_alerts_to_loki,
    get_all_alerts_for_ensemble_from_analysis_id,
    clean_up_alerts_in_loki,
)
from app.logger import LOGGER
from app.database import get_db
from app.models.benchmarking import (
    BenchmarkingResultTransferObject,
    BenchmarkingIntermediateResult,
    save_intermedaite_result,
    save_intermedaite_result,
    get_all_intermediate_results_for_ensemble_and_id,
)
from datetime import datetime

router = APIRouter(prefix="/ensemble")


@router.post("/setup")
async def setup_ensembles(ensembleData: EnsembleCreate, db=Depends(get_db)):
    ensemble = Ensemble(
        name=ensembleData.name,
        description=ensembleData.description,
        technique_id=ensembleData.technique,
        status=STATUS.IDLE.value,
    )
    await add_ensemble(db, ensemble)

    responses = []
    for id in ensembleData.container_ids:
        response: HTTPResponse = await ensemble.add_container(db, id)
        if response.status_code != 400 and response.status_code != 500:
            message = f"successfully added container {id} to ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message = (
                f"Did not add container {id} to ensemble {ensemble.id} successfully"
            )
            responses.append(create_generic_response_message_for_ensemble(message, 500))
    return JSONResponse(content={"content": responses}, status_code=200)


@router.delete("/remove/{ensemble_id}")
async def remove_ensemble_endpoint(ensemble_id: int, db=Depends(get_db)):
    ensemble: Ensemble = await get_ensemble_by_id(db, ensemble_id)
    ids_ensembles: list[EnsembleIds] = await get_all_ensemble_container(db)
    container_id_list = [
        ids_ensemble.ids_system_id
        for ids_ensemble in ids_ensembles
        if ids_ensemble.ensemble_id == ensemble_id
    ]
    container_list: list[IdsSystem] = [
        await get_ids_system_by_id(db=db, id=id) for id in container_id_list
    ]
    responses = []
    for container in container_list:
        # deregister from ensemble and stop running analysis if one is running
        response: HTTPResponse = await deregister_container_from_ensemble(container)
        if response.status_code != 400 and response.status_code != 500:
            message = f"message successfully removed container {container.id} from ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message = f" Did not remove container {container.id} from ensemble {ensemble.id} successfully"
            responses.append(create_generic_response_message_for_ensemble(message, 500))
    await remove_ensemble(db, ensemble)
    return JSONResponse(content={"content": responses}, status_code=200)


# TODO 5: update all returns to use new helper methdos (create_response_message/error) or delte helper methods


@router.post("/analysis/static")
async def start_static_ensemble_analysis(
    static_analysis_data: StaticAnalysisData, db=Depends(get_db)
):
    ensemble: Ensemble = await get_ensemble_by_id(db, static_analysis_data.ensemble_id)
    containers: list[IdsSystem] = await ensemble.get_assigned_containers(db)
    for container in containers:
        if container.status != STATUS.IDLE.value:
            message = f"container with id {container.id} is not Idle!, aborting"
            return create_response_error(message, 500)

        if not await container.is_available(db):
            message = f"container with id {container.id} is not available! Check if it should be deleted"
            return create_response_error(message, status_code=500)
        await update_sendig_logs_status(
            db=db,
            container=container,
            ensemble=ensemble,
            status=ANALYSIS_STATUS.PROCESSING.value,
        )
    await ensemble.generate_new_analysis_id(db)
    responses: list[HTTPResponse] = await ensemble.start_static_analysis(
        db=db, dataset_id=static_analysis_data.dataset_id
    )
    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [
        {"content": r.body.decode("utf-8"), "status_code": r.status_code}
        for r in responses
    ]
    # set container status to active/idle afterwards before
    await update_ensemble_status(db, ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)


@router.post("/analysis/network")
async def start_network_ensemble_analysis(
    network_analysis_data: NetworkAnalysisData, db=Depends(get_db)
):
    ensemble: Ensemble = await get_ensemble_by_id(db, network_analysis_data.ensemble_id)
    containers: list[IdsSystem] = await ensemble.get_assigned_containers(db)

    for container in containers:
        if container.status != STATUS.IDLE.value:
            return create_response_error(
                f"container with id {container.id} is not Idle!, aborting",
                status_code=500,
            )

        if not await container.is_available(db):
            content = f"container with id {container.id} is not available! Check if it should be deleted"
            return create_response_error(content, status_code=500)
        await update_sendig_logs_status(
            db=db,
            container=container,
            ensemble=ensemble,
            status=ANALYSIS_STATUS.PROCESSING.value,
        )

    await ensemble.generate_new_analysis_id(db)
    responses: list[HTTPResponse] = await ensemble.start_network_analysis(
        db=db, network_analysis_data=network_analysis_data
    )
    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [
        {"content": r.body.decode("utf-8"), "status_code": r.status_code}
        for r in responses
    ]
    await update_ensemble_status(db, ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)


@router.post("/analysis/stop")
async def stop_ensemble_analysis(stop_data: stop_analysisData, db=Depends(get_db)):
    ensemble: Ensemble = await get_ensemble_by_id(db, stop_data.ensemble_id)
    containers: list[IdsSystem] = await ensemble.get_assigned_containers(db)

    responses = []

    for container in containers:
        response: HTTPResponse = await container.stop_analysis()

        if response.status_code == 200:
            message = f"Successfully stopped analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message = f"Could not stop analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 500))

        await update_sendig_logs_status(
            db=db,
            container=container,
            ensemble=ensemble,
            status=ANALYSIS_STATUS.IDLE.value,
        )
    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.IDLE.value)
    return JSONResponse(content={"content": responses}, status_code=200)


@router.post("/analysis/finished")
async def finished_ensemble_analysis(
    analysisFinishedData: AnalysisFinishedData, db=Depends(get_db)
):
    container: IdsSystem = await get_ids_system_by_id(
        db, analysisFinishedData.container_id
    )
    ensemble: Ensemble = await get_ensemble_by_id(db, analysisFinishedData.ensemble_id)
    await update_sendig_logs_status(
        db=db, container=container, ensemble=ensemble, status=ANALYSIS_STATUS.IDLE.value
    )
    await update_ids_status(db, STATUS.IDLE.value, container)
    if await ensemble.container_is_last_one_running(db=db, container=container):
        await update_ensemble_status(db, STATUS.IDLE.value, ensemble)
        await ensemble.unset_analysis_id(db)
    return JSONResponse(
        {
            "message": f"Successfully finished analysis for esemble {analysisFinishedData.ensemble_id} and container {analysisFinishedData.container_id}"
        },
        status_code=200,
    )


@router.post("/publish/alerts")
async def receive_alerts_from_ids_for_ensemble(
    alert_data: AlertData, backgroundtasks: BackgroundTasks, db=Depends(get_db)
):
    container: IdsSystem = await get_ids_system_by_id(db=db, id=alert_data.container_id)
    ensemble: Ensemble = await get_ensemble_by_id(db=db, id=alert_data.ensemble_id)
    LOGGER.debug(f"analysis-type: {alert_data.analysis_type}")
    LOGGER.debug(f"Received Logs for ensemble {ensemble.name}")
    labels = {
        "container_name": container.name,
        "analysis_type": alert_data.analysis_type,
        "ensemble_name": ensemble.name,
        "logging": "alerts",
        "ensemble_analysis_id": ensemble.current_analysis_id,
    }
    analysis_is_static = (
        True
        if alert_data.dataset_id != None and alert_data.analysis_type == "static"
        else False
    )
    if analysis_is_static:
        dataset = await get_dataset_by_id(db=db, dataset_id=alert_data.dataset_id)
        labels["dataset"] = dataset.name
    alerts = [
        Alert(
            time=alert.time,
            destination_ip=alert.destination_ip,
            destination_port=alert.destination_port,
            source_ip=alert.source_ip,
            source_port=alert.source_port,
            severity=alert.severity,
            type=alert.type,
            message=alert.message,
        )
        for alert in alert_data.alerts
    ]
    LOGGER.debug(f"Found {len(alerts)} alerts for container {container.name}")

    response = await push_alerts_to_loki(alerts=alerts, labels=labels)
    if response.status_code not in [200, 204]:
        LOGGER.error("Could not push logs to loki effectively")
        return JSONResponse(
            {"error": "Could not push logs to loki for container"}, status_code=500
        )

    if analysis_is_static:
        LOGGER.debug("Static analysis data received")
        await update_sendig_logs_status(
            db=db,
            container=container,
            ensemble=ensemble,
            status=ANALYSIS_STATUS.IDLE.value,
        )
        intermediate_result = BenchmarkingIntermediateResult(
            ensemble_name=ensemble.name,
            ensemble_uuid=ensemble.current_analysis_id,
            container_name=container.name,
            start_time=alert_data.start_time,
            stop_time=alert_data.stop_time,
        )
        await save_intermedaite_result(db, intermediate_result)
        if not await last_container_sending_logs(
            db=db, container=container, ensemble=ensemble
        ):
            LOGGER.debug(f"Successfully pushed alerts for container {container.name}")
            LOGGER.debug(f"{container.name} is not the last running container")
            return JSONResponse(
                {
                    "content": f"Successfully pushed alerts for container {container.name}"
                },
                status_code=200,
            )
        else:
            LOGGER.debug(f"{container.name} is the last container running")
            # get all alerts including the ones form the current container
            all_alerts: dict = await get_all_alerts_for_ensemble_from_analysis_id(
                ensemble.current_analysis_id
            )
            # calculate which alerts the ensemble now alerts according to its technique
            ensembled_alerts = (
                await ensemble.ensemble_technique.execute_technique_by_name_on_alerts(
                    alerts_dict=all_alerts, ensemble=ensemble
                )
            )
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = "None"
            # cleanup loki alerts of the individiual containers
            backgroundtasks.add_task(
                clean_up_alerts_in_loki, ensemble.current_analysis_id
            )
            # push the logs for the ensemble
            backgroundtasks.add_task(
                push_alerts_to_loki, ensembled_alerts, labels=labels
            )
            all_intermediate_results = (
                await get_all_intermediate_results_for_ensemble_and_id(
                    db, ensemble.current_analysis_id, ensemble.name
                )
            )
            result_with_first_analysis_begin = min(
                all_intermediate_results,
                key=lambda r: datetime.strptime(r.start_time, "%d-%m-%Y %H:%M:%S.%f"),
            )
            result_with_last_stopped_analysis = max(
                all_intermediate_results,
                key=lambda r: datetime.strptime(r.stop_time, "%d-%m-%Y %H:%M:%S.%f"),
            )
            benchmarking_results = BenchmarkingResultTransferObject(
                alerts=ensembled_alerts,
                dataset_id=alert_data.dataset_id,
                start_time=result_with_first_analysis_begin.start_time,
                stop_time=result_with_last_stopped_analysis.stop_time,
            )
            # Fetch ensemble technique name
            ensemble_technique_name = (
                ensemble.ensemble_technique.name
                if ensemble.ensemble_technique
                else None
            )
            backgroundtasks.add_task(
                calculate_evaluation_metrics_and_push,
                db=db,
                benchmarking_results=benchmarking_results,
                ensemble_name=ensemble.name,
                ensemble_technique_name=ensemble_technique_name,
            )
            return JSONResponse(
                {"content": f"Successfully pushed alerts for ensemble {ensemble.name}"},
                status_code=200,
            )
    else:
        LOGGER.debug("Network analysis data received")
        LOGGER.debug(f"{container.name} got {len(alerts)}")
        if not await last_container_sending_logs(
            db=db, container=container, ensemble=ensemble
        ):
            return JSONResponse(
                {
                    "content": f"Successfully pushed alerts for container {container.name}"
                },
                status_code=200,
            )
        else:
            all_alerts: dict = await get_all_alerts_for_ensemble_from_analysis_id(
                ensemble.current_analysis_id
            )
            ensembled_alerts = (
                await ensemble.ensemble_technique.execute_technique_by_name_on_alerts(
                    alerts_dict=all_alerts, ensemble=ensemble
                )
            )
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = "None"
            await clean_up_alerts_in_loki(ensemble.current_analysis_id)
            backgroundtasks.add_task(
                push_alerts_to_loki, ensembled_alerts, labels=labels
            )
            # assign new uuid to distinguish the next alert round from the current one
            await ensemble.generate_new_analysis_id(db)

            # update the satus of all containers again to be processing
            all_containers_in_ensemble = await ensemble.get_assigned_containers(db)
            for c in all_containers_in_ensemble:
                await update_sendig_logs_status(
                    db=db,
                    container=c,
                    ensemble=ensemble,
                    status=ANALYSIS_STATUS.PROCESSING.value,
                )
            # the refresh here is mandatory as the udpate_sending logs because of lazy loading
            message = f"Successfully pushed alerts for ensemble {ensemble.name}"
            return JSONResponse({"content": message}, status_code=200)
