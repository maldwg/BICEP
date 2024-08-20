import asyncio
from http.client import HTTPResponse
import json

from ..metrics import calculate_evaluation_metrics_for_ensemble
from ..bicep_utils.models.ids_base import Alert
from ..models.ensemble_ids import get_all_ensemble_container, EnsembleIds
from ..models.configuration import Configuration, get_config_by_id
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from fastapi import APIRouter, Depends, Response
from fastapi.encoders import jsonable_encoder
from ..database import get_db
from ..validation.models import AlertData, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, StopAnalysisData, AnalysisFinishedData
from ..models.ensemble import get_all_ensembles, Ensemble, add_ensemble, get_ensemble_by_id, remove_ensemble, update_ensemble_status
from ..models.ids_container import IdsContainer
from ..models.dataset import Dataset, get_dataset_by_id
import httpx 
from ..utils import deregister_container_from_ensemble, find_free_port, STATUS, get_container_host, create_response_error, create_response_message, create_generic_response_message_for_ensemble
from fastapi.responses import JSONResponse
from ..prometheus import push_evaluation_metrics_to_prometheus
from ..loki import push_alerts_to_loki
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
    container = get_container_by_id(db, analysisFinishedData.container_id)
    ensemble: Ensemble = get_ensemble_by_id(analysisFinishedData.ensemble_id, db)
    await ensemble.stop_metric_collection(db)
    await update_container_status(STATUS.IDLE.value, container, db)
    # TODO: check if this was the last container that ran, if yes update ensemble status and stop ensemble metric collection
    await update_ensemble_status(STATUS.IDLE.value, ensemble, db)
    return Response(content=f"Successfully finished analysis for esemble {analysisFinishedData.ensemble_id} and container {analysisFinishedData.container_id}", status_code=200)

# TODO 0: ensemble ends only one container data not all as metrics (cpou, memory) ,  
@router.post("/publish/alerts")
async def receive_alerts_from_ids(alert_data: AlertData, db=Depends(get_db)):
    container = get_container_by_id(db=db, id=alert_data.container_id)
    ensemble = get_ensemble_by_id(db=db, id=alert_data.ensemble_id)    
    labels = {
        "container_name": container.name,
        "analysis_type": alert_data.analysis_type,
        "ensemble_name": ensemble.name,
        "logging": "alerts",
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
        # TODO 0: implement logic for receiving alerts 
        # TODO 0: metrics start/stop might be buggy

        # check if other containers are still running --> if no and this is last, then send the logs -> DOWNSIDE: if relatively same tempo --> doubly calculating
        # otherwise: check if in timeframe there was already a push for this ensemble from all the other container ids? ?
        # otherwise label/counter for the ensemble to knwo which label to assign / coordinate
   
        # save intermediate results until all container are stopped and have send data
        # get the majority vote method to know how to rank the systems
        # calculate metrics
        pass
        # await push_evaluation_metrics_to_prometheus()
    await push_alerts_to_loki(alerts=alerts, labels=labels)


    if alert_data.analysis_type == "static":
        metrics = await calculate_evaluation_metrics_for_ensemble()
        if alert_data.dataset_id != None:
            pass
            await push_evaluation_metrics_to_prometheus(metrics, container_name=container.name, ensemble_name=ensemble.name, dataset_name=dataset.name)
        else:
            pass
            await push_evaluation_metrics_to_prometheus(metrics, container_name=container.name, ensemble_name=ensemble.name, dataset_name=None)