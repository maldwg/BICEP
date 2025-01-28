import asyncio
from http.client import HTTPResponse
import json

from ..metrics import calculate_evaluation_metrics
from ..bicep_utils.models.ids_base import Alert
from ..models.ensemble_ids import get_all_ensemble_container, EnsembleIds, update_sendig_logs_status, last_container_sending_logs
from ..models.configuration import Configuration, get_config_by_id
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from ..models.ensemble_technique import EnsembleTechnique, get_ensemble_technique_by_id
from fastapi import APIRouter, Depends, Response
from fastapi.encoders import jsonable_encoder
import uuid
from ..database import get_db
from ..validation.models import AlertData, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, stop_analysisData, AnalysisFinishedData
from ..models.ensemble import get_all_ensembles, Ensemble, add_ensemble, get_ensemble_by_id, remove_ensemble, update_ensemble_status
from ..models.ids_container import IdsContainer
from ..models.dataset import Dataset, get_dataset_by_id
import httpx 
from ..utils import deregister_container_from_ensemble, find_free_port, STATUS, ANALYSIS_STATUS ,create_response_error, create_response_message, create_generic_response_message_for_ensemble
from fastapi.responses import JSONResponse
from ..prometheus import push_evaluation_metrics_to_prometheus
from ..loki import push_alerts_to_loki, get_alerts_from_analysis_id, clean_up_alerts_in_loki
router = APIRouter(
    prefix="/ensemble"
)

@router.post("/setup")
async def setup_ensembles(ensembleData: EnsembleCreate,db=Depends(get_db)):
    ensemble = Ensemble(
        name=ensembleData.name,
        description=ensembleData.description, 
        technique_id=ensembleData.technique,
        status=STATUS.IDLE.value)
    await add_ensemble(ensemble, db)

    responses = []
    for id in ensembleData.container_ids:
        response: HTTPResponse = await ensemble.add_container(id, db)
        if response.status_code != 400 and response.status_code != 500:
            message=f"successfully added container {id} to ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message=f"Did not add container {id} to ensemble {ensemble.id} successfully"
            responses.append(create_generic_response_message_for_ensemble(message, 500))
    return JSONResponse(content={"content": responses}, status_code=200)

@router.delete("/remove/{ensemble_id}")
async def remove_ensemble(ensemble_id: int,db=Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(ensemble_id, db)
    ids_ensembles: list[EnsembleIds] = get_all_ensemble_container(db)
    container_id_list = [ids_ensemble.ids_container_id  for ids_ensemble in ids_ensembles if ids_ensemble.ensemble_id == ensemble_id]
    container_list: list[IdsContainer] = [ get_container_by_id(db=db, id=id) for id in container_id_list]
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
    remove_ensemble(ensemble, db)
    return JSONResponse(content={"content": responses}, status_code=200)

# TODO 5: update all returns to use new helper methdos (create_response_message/error) or delte helper methods

@router.post("/analysis/static")
async def start_static_ensemble_analysis(static_analysis_data: StaticAnalysisData, db=Depends(get_db)):
    dataset: Dataset = get_dataset_by_id(db, static_analysis_data.dataset_id)
    
    ensemble: Ensemble = get_ensemble_by_id(static_analysis_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)
    for container in containers:
        if container.status != STATUS.IDLE.value:
            print("test")
            message = f"container with id {container.id} is not Idle!, aborting"
            return create_response_error(message, 500)
        
        if not await container.is_available():
            message = f"container with id {container.id} is not available! Check if it should be deleted"
            return create_response_error(message, status_code=500)

        await update_sendig_logs_status(container=container, ensemble=ensemble,db=db, status=ANALYSIS_STATUS.PROCESSING.value )

    # set new uuid to identify the new run
    ensemble.current_analysis_id = str(uuid.uuid4())
    


    responses: list[HTTPResponse] = await ensemble.start_static_analysis(dataset=dataset, db=db)
    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [ {"content": r.body.decode("utf-8"), "status_code": r.status_code} for r in responses]
    # set container status to active/idle afterwards before
    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)

@router.post("/analysis/network")
async def start_network_ensemble_analysis(network_analysis_data: NetworkAnalysisData, db = Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(network_analysis_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    for container in containers:
        if container.status != STATUS.IDLE.value:
            return create_response_error(f"container with id {container.id} is not Idle!, aborting", status_code=500)
        
        if not await container.is_available():
         content=f"container with id {container.id} is not available! Check if it should be deleted"
         return create_response_error(content, status_code=500)

        await update_sendig_logs_status(container=container, ensemble=ensemble,db=db, status=ANALYSIS_STATUS.PROCESSING.value)

    ensemble.current_analysis_id = str(uuid.uuid4())

    responses: list[HTTPResponse] = await ensemble.start_network_analysis(db=db, network_analysis_data=network_analysis_data)

    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [ {"content": r.body.decode("utf-8"), "status_code": r.status_code} for r in responses]
    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)


@router.post("/analysis/stop")
async def stop_ensemble_analysis(stop_data: stop_analysisData, db=Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(stop_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    responses = []

    for container in containers:
        response: HTTPResponse = await container.stop_analysis()
        
        if response.status_code == 200:
            await update_container_status(STATUS.IDLE.value, container, db)
            message = f"Successfully stopped analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message = f"Could not stop analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 500))

        await update_sendig_logs_status(container=container, ensemble=ensemble,db=db, status=ANALYSIS_STATUS.IDLE.value)

    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.IDLE.value)
    return JSONResponse(content={"content": responses}, status_code=200)

@router.post("/analysis/finished")
async def finished_ensemble_analysis(analysisFinishedData: AnalysisFinishedData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, analysisFinishedData.container_id)
    ensemble: Ensemble = get_ensemble_by_id(analysisFinishedData.ensemble_id, db)
    await update_sendig_logs_status(container=container, ensemble=ensemble,db=db, status=ANALYSIS_STATUS.IDLE.value)
    print(f"Updated status of {container.name} to IDLE")
    await update_container_status(STATUS.IDLE.value, container, db)
    if await ensemble.container_is_last_one_running(container=container, db=db):
        await update_ensemble_status(STATUS.IDLE.value, ensemble, db)
        print(f"Updated status of ensemble {ensemble.name} to IDLE")
        ensemble.current_analysis_id = None
    return JSONResponse({"message": f"Successfully finished analysis for esemble {analysisFinishedData.ensemble_id} and container {analysisFinishedData.container_id}"}, status_code=200)

@router.post("/publish/alerts")
async def receive_alerts_from_ids_for_ensemble(alert_data: AlertData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db=db, id=alert_data.container_id)
    ensemble: Ensemble = get_ensemble_by_id(db=db, id=alert_data.ensemble_id)
    labels = {
        "container_name": container.name,
        "analysis_type": alert_data.analysis_type,
        "ensemble_name": ensemble.name,
        "logging": "alerts",
        "ensemble_analysis_id": ensemble.current_analysis_id,
    }
    if alert_data.dataset_id != None:
        dataset = get_dataset_by_id(dataset_id=alert_data.dataset_id, db=db)
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
    # push alerts first, to ensure that enough tie has been passed for other containers to upload their logs
    response = await push_alerts_to_loki(alerts=alerts, labels=labels)
    if response.status_code != 204:
        return JSONResponse({"content": "Could not push logs to loki for container"},status_code=500)

    if alert_data.analysis_type == "static":
        await update_sendig_logs_status(container=container, ensemble=ensemble,db=db, status=ANALYSIS_STATUS.IDLE.value)
        if not await last_container_sending_logs(container=container, ensemble=ensemble, db=db):
            print(f"Successfully pushed alerts for container {container.name}")
            return JSONResponse({"content": f"Successfully pushed alerts for container {container.name}"}, status_code=200) 
        else:
            all_alerts: dict = await get_alerts_from_analysis_id(ensemble.current_analysis_id)
            ensembled_alerts = await ensemble.ensemble_technique.execute_technique_by_name_on_alerts(alerts_dict=all_alerts, ensemble=ensemble)
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = "None"
            # cleanup and reupload alerts so that only the weighted and ensembled ones are now available for the ensemble
            asyncio.create_task(clean_up_alerts_in_loki(ensemble.current_analysis_id))
            asyncio.create_task(push_alerts_to_loki(alerts=ensembled_alerts, labels=labels))
            metrics = await calculate_evaluation_metrics(dataset=dataset, alerts=ensembled_alerts)
            asyncio.create_task(push_evaluation_metrics_to_prometheus(metrics, ensemble_name=ensemble.name, dataset_name=dataset.name))
            return JSONResponse({"content": f"Successfully pushed alerts for ensemble {ensemble.name}"}, status_code=200)    
    else:
        print(f"{container.name} got {len(alerts)}")
        await update_sendig_logs_status(container=container, ensemble=ensemble,db=db, status=ANALYSIS_STATUS.LOGS_SENT.value)
        if not await last_container_sending_logs(container=container, ensemble=ensemble, db=db):
            print(f"I am not the last one {container.name}")
            return JSONResponse({"content": f"Successfully pushed alerts for container {container.name}"}, status_code=200)       
        else:
            print(f"I am the last running container: {container.name}")
            all_alerts: dict = await get_alerts_from_analysis_id(ensemble.current_analysis_id)
            ensembled_alerts = await ensemble.ensemble_technique.execute_technique_by_name_on_alerts(alerts_dict=all_alerts, ensemble=ensemble)
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = "None"
            # cleanup and reupload alerts so that only the weighted and ensembled ones are now available for the ensemble
            # await clean_up_alerts_in_loki(ensemble.current_analysis_id)
            await push_alerts_to_loki(alerts=ensembled_alerts, labels=labels)
            # assign new uuid to distinguish the next alert round from the current one
            ensemble.current_analysis_id = str(uuid.uuid4())
            # update al satus to be processing again
            all_containers_in_ensemble = ensemble.get_containers(db)
            for c in all_containers_in_ensemble:
                await update_sendig_logs_status(container=c, ensemble=ensemble,db=db, status=ANALYSIS_STATUS.PROCESSING.value)
            return JSONResponse({"content": f"Successfully pushed alerts for ensemble {ensemble.name}"}, status_code=200)    
        
# TODO 5: do not allow in frontend/backend to stop the analysis of a container that is running for an ensemble