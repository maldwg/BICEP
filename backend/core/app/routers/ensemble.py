import asyncio
from http.client import HTTPResponse
import json

from ..metrics import calculate_evaluation_metrics
from ..bicep_utils.models.ids_base import Alert
from ..models.ensemble_ids import get_all_ensemble_container, EnsembleIds, get_ensemble_ids_by_ids, update_sendig_logs_status, last_container_sending_logs
from ..models.configuration import Configuration, get_config_by_id
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from ..models.ensemble_technique import EnsembleTechnique, get_ensemble_technique_by_id
from fastapi import APIRouter, Depends, Response, BackgroundTasks
from fastapi.encoders import jsonable_encoder
import uuid
from ..validation.models import AlertData, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, stop_analysisData, AnalysisFinishedData
from ..models.ensemble import get_all_ensembles, Ensemble, add_ensemble, get_ensemble_by_id, remove_ensemble, update_ensemble_status, generate_new_analysis_id, unset_analysis_id
from ..models.ids_container import IdsContainer
from ..models.dataset import Dataset, get_dataset_by_id
import httpx 
from ..utils import calculate_evaluation_metrics_and_push, deregister_container_from_ensemble, find_free_port, STATUS, ANALYSIS_STATUS ,create_response_error, create_response_message, create_generic_response_message_for_ensemble
from fastapi.responses import JSONResponse
from ..prometheus import push_evaluation_metrics_to_prometheus
from ..loki import push_alerts_to_loki, get_all_alerts_for_ensemble_from_analysis_id, clean_up_alerts_in_loki
from ..logger import LOGGER

router = APIRouter(
    prefix="/ensemble"
)

@router.post("/setup")
async def setup_ensembles(ensembleData: EnsembleCreate):
    ensemble = Ensemble(
        name=ensembleData.name,
        description=ensembleData.description, 
        technique_id=ensembleData.technique,
        status=STATUS.IDLE.value)
    await add_ensemble(ensemble)

    responses = []
    for id in ensembleData.container_ids:
        response: HTTPResponse = await ensemble.add_container(id)
        if response.status_code != 400 and response.status_code != 500:
            message=f"successfully added container {id} to ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message=f"Did not add container {id} to ensemble {ensemble.id} successfully"
            responses.append(create_generic_response_message_for_ensemble(message, 500))
    return JSONResponse(content={"content": responses}, status_code=200)

@router.delete("/remove/{ensemble_id}")
async def remove_ensemble_endpoint(ensemble_id: int):
    ensemble: Ensemble = await get_ensemble_by_id(ensemble_id)
    ids_ensembles: list[EnsembleIds] = await get_all_ensemble_container()
    container_id_list = [ids_ensemble.ids_container_id  for ids_ensemble in ids_ensembles if ids_ensemble.ensemble_id == ensemble_id]
    container_list: list[IdsContainer] = [ await get_container_by_id(id=id) for id in container_id_list]
    responses = []
    for container in container_list:
        # deregister from ensemble and stop running analysis if one is running
        response: HTTPResponse = await deregister_container_from_ensemble(container)
        if response.status_code != 400 and response.status_code != 500:
            message=f"message successfully removed container {container.id} from ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message=f" Did not remove container {container.id} from ensemble {ensemble.id} successfully"
            responses.append(create_generic_response_message_for_ensemble(message, 500))    
    LOGGER.debug(responses)
    await remove_ensemble(ensemble)
    return JSONResponse(content={"content": responses}, status_code=200)

# TODO 5: update all returns to use new helper methdos (create_response_message/error) or delte helper methods

@router.post("/analysis/static")
async def start_static_ensemble_analysis(static_analysis_data: StaticAnalysisData):
    dataset: Dataset = await get_dataset_by_id(static_analysis_data.dataset_id)
    
    ensemble: Ensemble = await get_ensemble_by_id(static_analysis_data.ensemble_id)
    containers: list[IdsContainer] = await ensemble.get_assigned_containers()
    for container in containers:
        if container.status != STATUS.IDLE.value:
            message = f"container with id {container.id} is not Idle!, aborting"
            return create_response_error(message, 500)
        
        if not await container.is_available():
            message = f"container with id {container.id} is not available! Check if it should be deleted"
            return create_response_error(message, status_code=500)
        await update_sendig_logs_status(container=container, ensemble=ensemble, status=ANALYSIS_STATUS.PROCESSING.value )
   
    await generate_new_analysis_id(ensemble)

    # test
    ensemble: Ensemble = await get_ensemble_by_id(static_analysis_data.ensemble_id)


    responses: list[HTTPResponse] = await ensemble.start_static_analysis(dataset=dataset)
    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [ {"content": r.body.decode("utf-8"), "status_code": r.status_code} for r in responses]
    # set container status to active/idle afterwards before

    # test
    ensemble: Ensemble = await get_ensemble_by_id(static_analysis_data.ensemble_id)

    await update_ensemble_status(ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)

@router.post("/analysis/network")
async def start_network_ensemble_analysis(network_analysis_data: NetworkAnalysisData):
    ensemble: Ensemble = await get_ensemble_by_id(network_analysis_data.ensemble_id )
    containers: list[IdsContainer] = await ensemble.get_assigned_containers()

    for container in containers:
        if container.status != STATUS.IDLE.value:
            return create_response_error(f"container with id {container.id} is not Idle!, aborting", status_code=500)
        
        if not await container.is_available():
         content=f"container with id {container.id} is not available! Check if it should be deleted"
         return create_response_error(content, status_code=500)
        e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
        LOGGER.debug(f"container {e_ids.ids_container_id} has the status {e_ids.status} = prolly idle")
        await update_sendig_logs_status(container=container, ensemble=ensemble, status=ANALYSIS_STATUS.PROCESSING.value)
        e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
        LOGGER.debug(f"container {e_ids.ids_container_id} has the status {e_ids.status} = processing")
    # test
    ensemble: Ensemble = await get_ensemble_by_id(network_analysis_data.ensemble_id)

    await generate_new_analysis_id(ensemble)

    # test
    ensemble: Ensemble = await get_ensemble_by_id(network_analysis_data.ensemble_id)

    responses: list[HTTPResponse] = await ensemble.start_network_analysis(network_analysis_data=network_analysis_data)

    # test
    ensemble: Ensemble = await get_ensemble_by_id(network_analysis_data.ensemble_id)

    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [ {"content": r.body.decode("utf-8"), "status_code": r.status_code} for r in responses]
    await update_ensemble_status(ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)


@router.post("/analysis/stop")
async def stop_ensemble_analysis(stop_data: stop_analysisData):
    ensemble: Ensemble = await get_ensemble_by_id(stop_data.ensemble_id)
    containers: list[IdsContainer] = await ensemble.get_assigned_containers()

    responses = []

    for container in containers:
        response: HTTPResponse = await container.stop_analysis()
        
        if response.status_code == 200:
            message = f"Successfully stopped analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message = f"Could not stop analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 500))
        e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
        LOGGER.debug(f"stopping: container {e_ids.ids_container_id} has the status {e_ids.status} ")
        await update_sendig_logs_status(container=container, ensemble=ensemble, status=ANALYSIS_STATUS.IDLE.value)
        e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
        LOGGER.debug(f"stopping: container {e_ids.ids_container_id} has the status {e_ids.status} ")
    await update_ensemble_status(ensemble=ensemble, status=STATUS.IDLE.value)
    return JSONResponse(content={"content": responses}, status_code=200)

@router.post("/analysis/finished")
async def finished_ensemble_analysis(analysisFinishedData: AnalysisFinishedData):
    container: IdsContainer = await get_container_by_id(analysisFinishedData.container_id)
    ensemble: Ensemble = await get_ensemble_by_id(analysisFinishedData.ensemble_id)
    e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
    LOGGER.debug(f"finished: container {e_ids.ids_container_id} has the status {e_ids.status} = whatever")
    await update_sendig_logs_status(container=container, ensemble=ensemble, status=ANALYSIS_STATUS.IDLE.value)
    e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
    LOGGER.debug(f"finished: container {e_ids.ids_container_id} has the status {e_ids.status} = IDLE")
    #test 
    container: IdsContainer = await get_container_by_id(analysisFinishedData.container_id)
    LOGGER.debug(f"finished {container.name} status is {container.status} = wahtever ")
    await update_container_status(STATUS.IDLE.value, container)
    LOGGER.debug(f"finished {container.name} status is {container.status} != IDLE")
    #test 
    container: IdsContainer = await get_container_by_id(analysisFinishedData.container_id)
    LOGGER.debug(f"finished {container.name} status is {container.status} should be IDLE ")

    if await ensemble.container_is_last_one_running(container=container):
        LOGGER.debug(f"container is the last one {container.name}, therefor shutting down the eneseble")
        await update_ensemble_status(STATUS.IDLE.value, ensemble)     
        ensemble: Ensemble = await get_ensemble_by_id(analysisFinishedData.ensemble_id) 
        LOGGER.debug(f"ensemble has analysis id {ensemble.current_analysis_id}") 
        await unset_analysis_id(ensemble)
        LOGGER.debug(f"ensemble has analysis id {ensemble.current_analysis_id}, should be NOne") 

    return JSONResponse({"message": f"Successfully finished analysis for esemble {analysisFinishedData.ensemble_id} and container {analysisFinishedData.container_id}"}, status_code=200)

@router.post("/publish/alerts")
async def receive_alerts_from_ids_for_ensemble(alert_data: AlertData, backgroundtasks: BackgroundTasks):
    container: IdsContainer = await get_container_by_id(id=alert_data.container_id)
    ensemble: Ensemble = await get_ensemble_by_id(id=alert_data.ensemble_id)
    # LOGGER.debug(f"analysis-type: {alert_data.analysis_type}")
    # LOGGER.debug(f"Received Logs for ensemble {ensemble.name}")
    labels = {
        "container_name": container.name,
        "analysis_type": alert_data.analysis_type,
        "ensemble_name": ensemble.name,
        "logging": "alerts",
        "ensemble_analysis_id": ensemble.current_analysis_id,
    }
    analysis_is_static = True if alert_data.dataset_id != None and alert_data.analysis_type == "static" else False
    if analysis_is_static:
        dataset = await get_dataset_by_id(dataset_id=alert_data.dataset_id)
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
            message=alert.message
            ) 
        for alert in alert_data.alerts
    ]        
    LOGGER.debug(f"Found {len(alerts)} alerts for container {container.name}")

    response = await push_alerts_to_loki(alerts=alerts, labels=labels)
    if response.status_code not in [200,204]:
        LOGGER.error("Could not push logs to loki effectively")
        return JSONResponse({"error": "Could not push logs to loki for container"},status_code=500)

    if analysis_is_static:
        LOGGER.debug("Static analysis data received")
        await update_sendig_logs_status(container=container, ensemble=ensemble,status=ANALYSIS_STATUS.IDLE.value)

        container: IdsContainer = await get_container_by_id(id=alert_data.container_id)
        ensemble: Ensemble = await get_ensemble_by_id(id=alert_data.ensemble_id)

        if not await last_container_sending_logs(container=container, ensemble=ensemble):
            LOGGER.debug(f"Successfully pushed alerts for container {container.name}")
            LOGGER.debug(f"{container.name} I am not the last Container")
            return JSONResponse({"content": f"Successfully pushed alerts for container {container.name}"}, status_code=200) 
        else:
            LOGGER.debug(f"{container.name} I am the last container running")
            # get all alerts including the ones form the current container
            all_alerts: dict = await get_all_alerts_for_ensemble_from_analysis_id(ensemble.current_analysis_id)
            # calculate which alerts the ensemble now alerts according to its technique
            ensembled_alerts = await ensemble.ensemble_technique.execute_technique_by_name_on_alerts(alerts_dict=all_alerts, ensemble=ensemble)
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = "None"
            # cleanup loki alerts of the individiual containers
            backgroundtasks.add_task(clean_up_alerts_in_loki, ensemble.current_analysis_id)
            # push the logs for the ensemble
            backgroundtasks.add_task(push_alerts_to_loki, ensembled_alerts, labels=labels)
            LOGGER.debug(f"Start calculating evaluation metrics for ensemble {ensemble.name} and dataset {dataset.name}")
            backgroundtasks.add_task(calculate_evaluation_metrics_and_push, dataset=dataset, alerts=ensembled_alerts,ensemble_name=ensemble.name)
            return JSONResponse({"content": f"Successfully pushed alerts for ensemble {ensemble.name}"}, status_code=200)    
    else:
        # LOGGER.debug("Network analysis data received")
        # LOGGER.debug(f"{container.name} got {len(alerts)}")
        e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
        LOGGER.debug(f"publish: container {e_ids.ids_container_id} has the status {e_ids.status}, should be PROCESSING ")
        await update_sendig_logs_status(container=container, ensemble=ensemble, status=ANALYSIS_STATUS.LOGS_SENT.value)
        e_ids = await get_ensemble_ids_by_ids(ensemble.id,container.id)
        LOGGER.debug(f"publish: container {e_ids.ids_container_id} has the status {e_ids.status}, sould be LOGS_SENT")
        container: IdsContainer = await get_container_by_id(id=alert_data.container_id)
        ensemble: Ensemble = await get_ensemble_by_id(id=alert_data.ensemble_id)
        if not await last_container_sending_logs(container=container, ensemble=ensemble):
            return JSONResponse({"content": f"Successfully pushed alerts for container {container.name}"}, status_code=200)       
        else:
            all_alerts: dict = await get_all_alerts_for_ensemble_from_analysis_id(ensemble.current_analysis_id)
            ensembled_alerts = await ensemble.ensemble_technique.execute_technique_by_name_on_alerts(alerts_dict=all_alerts, ensemble=ensemble)
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = "None"
            await clean_up_alerts_in_loki(ensemble.current_analysis_id)
            backgroundtasks.add_task(push_alerts_to_loki, ensembled_alerts, labels=labels)
            # assign new uuid to distinguish the next alert round from the current one
            ensemble.current_analysis_id = str(uuid.uuid4())
            # update the satus of all containers again to be processing
            all_containers_in_ensemble = await ensemble.get_assigned_containers()
            for c in all_containers_in_ensemble:
                await update_sendig_logs_status(container=c, ensemble=ensemble, status=ANALYSIS_STATUS.PROCESSING.value)
            return JSONResponse({"content": f"Successfully pushed alerts for ensemble {ensemble.name}"}, status_code=200)    