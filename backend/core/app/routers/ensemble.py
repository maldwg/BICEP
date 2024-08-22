import asyncio
from http.client import HTTPResponse
import json

from ..metrics import calculate_evaluation_metrics_for_ensemble
from ..bicep_utils.models.ids_base import Alert
from ..models.ensemble_ids import get_all_ensemble_container, EnsembleIds
from ..models.configuration import Configuration, get_config_by_id
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from ..models.ensemble_technique import EnsembleTechnique, get_ensemble_technique_by_id
from fastapi import APIRouter, Depends, Response
from fastapi.encoders import jsonable_encoder
import uuid
from ..database import get_db
from ..validation.models import AlertData, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, StopAnalysisData, AnalysisFinishedData
from ..models.ensemble import get_all_ensembles, Ensemble, add_ensemble, get_ensemble_by_id, remove_ensemble, update_ensemble_status
from ..models.ids_container import IdsContainer
from ..models.dataset import Dataset, get_dataset_by_id
import httpx 
from ..utils import deregister_container_from_ensemble, find_free_port, STATUS, get_container_host, create_response_error, create_response_message, create_generic_response_message_for_ensemble
from fastapi.responses import JSONResponse
from ..prometheus import push_evaluation_metrics_to_prometheus
from ..loki import push_alerts_to_loki, get_alerts_from_analysis_id, clean_up_alerts_in_loki, containers_already_pushed_to_loki
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
async def remove_ensembles(ensemble_id: int,db=Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(ensemble_id, db)
    ids_ensembles: list[EnsembleIds] = get_all_ensemble_container(db)
    container_id_list = [ids_ensemble.ids_container_id  for ids_ensemble in ids_ensembles if ids_ensemble.ensemble_id == ensemble_id]
    container_list: list[IdsContainer] = [ get_container_by_id(db=db, id=id) for id in container_id_list]
    responses = []
    await ensemble.stop_metric_collection(db)
    for container in container_list:
        # deregister from ensemble and stop running analysis if one is running
        response: HTTPResponse = await deregister_container_from_ensemble(container)
        if response.status_code != 400 and response.status_code != 500:
            message=f"message successfully removed container {id} from ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message=f" Did not remove container {id} from ensemble {ensemble.id} successfully"
            responses.append(create_generic_response_message_for_ensemble(message, 500))    
    remove_ensemble(ensemble, db)
    return JSONResponse(content={"content": responses}, status_code=200)

# TODO: update all returns to use new helper methdos (create_response_message/error)

@router.post("/analysis/static")
async def start_static_container_analysis(static_analysis_data: StaticAnalysisData, db=Depends(get_db)):
    dataset: Dataset = get_dataset_by_id(db, static_analysis_data.dataset_id)
    
    ensemble: Ensemble = get_ensemble_by_id(static_analysis_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    for container in containers:
        if container.status != STATUS.IDLE.value:
            message = f"container with id {container.id} is not Idle!, aborting"
            return create_response_error(message, 500)

    if ensemble.current_analysis_id == None:
        ensemble.current_analysis_id = str(uuid.uuid4())


    responses: list[HTTPResponse] = await ensemble.start_static_analysis(static_analysis_data=static_analysis_data, dataset=dataset, db=db)
    await ensemble.start_metric_collection(db)
    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [ {"content": r.body.decode("utf-8"), "status_code": r.status_code} for r in responses]
    # set container status to active/idle afterwards before
    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)

# TODO maybe: improve differentiation between ids anylssis so that in the frontend ewe can see which ids did not start and rollback?

@router.post("/analysis/network")
async def start_static_container_analysis(network_analysis_data: NetworkAnalysisData, db = Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(network_analysis_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    for container in containers:
        if container.status != STATUS.IDLE.value:
            return create_response_error(f"container with id {container.id} is not Idle!, aborting", status_code=500)

    if ensemble.current_analysis_id == None:
        ensemble.current_analysis_id = str(uuid.uuid4())

    responses: list[HTTPResponse] = await ensemble.start_network_analysis(db=db, network_analysis_data=network_analysis_data)
    await ensemble.start_metric_collection(db)

    # Parse Response objects as otherwise there is an issue as Response objects are not serializable
    content = [ {"content": r.body.decode("utf-8"), "status_code": r.status_code} for r in responses]
    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.ACTIVE.value)
    return JSONResponse(content={"content": content}, status_code=200)


@router.post("/analysis/stop")
async def stop_analysis(stop_data: StopAnalysisData, db=Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(stop_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    responses = []

    for container in containers:
        response: HTTPResponse = await container.stop_analysis(db)
        
        if response.status_code == 200:
            await update_container_status(STATUS.IDLE.value, container, db)
            message = f"Successfully stopped analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message = f"Could not stop analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 500))
    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.IDLE.value)
    await ensemble.stop_metric_collection(db)
    return JSONResponse(content={"content": responses}, status_code=200)

@router.post("/analysis/finished")
async def finished_analysis(analysisFinishedData: AnalysisFinishedData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, analysisFinishedData.container_id)
    ensemble: Ensemble = get_ensemble_by_id(analysisFinishedData.ensemble_id, db)
    await ensemble.stop_metric_collection(db)
    await update_container_status(STATUS.IDLE.value, container, db)
    if await ensemble.container_is_last_one_running(container=container, db=db):
        await update_ensemble_status(STATUS.IDLE.value, ensemble, db)
        ensemble.current_analysis_id = None
    return Response(content=f"Successfully finished analysis for esemble {analysisFinishedData.ensemble_id} and container {analysisFinishedData.container_id}", status_code=200)

@router.post("/publish/alerts")
async def receive_alerts_from_ids(alert_data: AlertData, db=Depends(get_db)):
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
            destination=alert.destination, 
            source=alert.source, 
            severity=alert.severity, 
            type=alert.type, 
            message=alert.message
            ) 
        for alert in alert_data.alerts
    ]        

    if alert_data.analysis_type == "static":
        if not await ensemble.container_is_last_one_running(container=container, db=db):
            await push_alerts_to_loki(alerts=alerts, labels=labels)
            return Response(content=f"Successfully pushed alerts for container {container.name}", status_code=200) 
        else:
            previous_alerts: list[list[Alert]] = await get_alerts_from_analysis_id(ensemble.current_analysis_id)
            all_alerts = previous_alerts.append(alerts)
            ensemble_technique: EnsembleTechnique = get_ensemble_technique_by_id(db=db,id=ensemble.ensemble_technique)
            ensembled_alerts = ensemble_technique.execute_technique_by_name_on_alerts(all_alerts)
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = None
            # cleanup and reupload alerts so that only the weighted and ensembled ones are now available for the ensemble
            await clean_up_alerts_in_loki(ensemble.current_analysis_id)
            await push_alerts_to_loki(alerts=ensembled_alerts, labels=labels)
            metrics = await calculate_evaluation_metrics_for_ensemble(ensembled_alerts)
            await push_evaluation_metrics_to_prometheus(metrics, ensemble_name=ensemble.name, dataset_name=dataset.name)
            return Response(content=f"Successfully pushed alerts for ensemble {ensemble.name}", status_code=200)    
    else:
        other_containers_in_ensemble = list(filter(lambda c: c.id != container.id ,ensemble.get_containers(db)))
        if await containers_already_pushed_to_loki(other_containers_in_ensemble):
            previous_alerts: list[list[Alert]] = await get_alerts_from_analysis_id(ensemble.current_analysis_id)
            all_alerts = previous_alerts.append(alerts)
            ensemble_technique: EnsembleTechnique = get_ensemble_technique_by_id(db=db,id=ensemble.ensemble_technique)
            ensembled_alerts = ensemble_technique.execute_technique_by_name_on_alerts(all_alerts)
            # label change signals that the logs are not from a container but the ensemble
            labels["container_name"] = None
            # cleanup and reupload alerts so that only the weighted and ensembled ones are now available for the ensemble
            await clean_up_alerts_in_loki(ensemble.current_analysis_id)
            await push_alerts_to_loki(alerts=ensembled_alerts, labels=labels)
            return Response(content=f"Successfully pushed alerts for ensemble {ensemble.name}", status_code=200)    
        else:
            await push_alerts_to_loki(alerts=alerts, labels=labels)
            return Response(content=f"Successfully pushed alerts for container {container.name}", status_code=200)    
        
# TODO 5: do not allow in frontend/backend to stop the analysis of a container that is running for an ensemble