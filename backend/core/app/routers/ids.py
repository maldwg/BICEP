import asyncio
from http.client import HTTPResponse
from fastapi import APIRouter, Depends, Response, BackgroundTasks
from ..database import get_db
from ..validation.models import AlertData, IdsContainerCreate, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, StopAnalysisData, AnalysisFinishedData
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from ..models.configuration import Configuration, get_config_by_id
from ..models.dataset import Dataset, get_dataset_by_id
from ..utils import get_stream_metric_tasks ,create_response_error, create_response_message, find_free_port, STATUS, get_container_host, parse_response_for_triggered_analysis, calculate_evaluation_metrics_and_push
import httpx 
import json 
from fastapi.encoders import jsonable_encoder
from ..prometheus import push_evaluation_metrics_to_prometheus
from ..metrics import calculate_evaluation_metrics
from ..loki import push_alerts_to_loki
from ..bicep_utils.models.ids_base import Alert
router = APIRouter(
    prefix="/ids"
)

# TODO: docker needs longer or cant take it at all when image needs to be pulled. solution ?

@router.post("/setup")
async def setup_ids(data: IdsContainerCreate, db=Depends(get_db), stream_metric_tasks=Depends(get_stream_metric_tasks)):
    
    free_port=find_free_port()
    if data.ruleset_id:
        ruleset_id = data.ruleset_id
    else:
        ruleset_id = None
    ids_container = IdsContainer(
        host=data.host,
        port=free_port,
        description=data.description,
        configuration_id=data.configuration_id,
        ids_tool_id=data.ids_tool_id,
        status=STATUS.ACTIVE.value,
        ruleset_id=ruleset_id
        )
    await ids_container.setup(db)
    await ids_container.start_metric_collection(db=db, stream_metric_tasks=stream_metric_tasks)
    return {"message": "setup done"}


@router.delete("/remove/{container_id}")
async def remove_container(container_id: int, db=Depends(get_db), stream_metric_tasks=Depends(get_stream_metric_tasks)):
    container: IdsContainer = get_container_by_id(db, container_id)
    await container.stop_metric_collection(db=db, stream_metric_tasks=stream_metric_tasks)
    await container.teardown(db)
    return {"message": "teardown done"}

@router.post("/analysis/static")
async def start_static_container_analysis(static_analysis_data: StaticAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, static_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return Response(content=f"container with id {container.id} is not Idle!, aborting", status_code=500)

    dataset: Dataset = get_dataset_by_id(db, static_analysis_data.dataset_id)
    form_data= {
            "container_id": (None, str(container.id), "application/json"),
            "dataset": (dataset.name, dataset.pcap_file, "application/octet-stream"),
            "dataset_id": (None, str(dataset.id), "application/json")
        }    
    response: HTTPResponse = await container.start_static_analysis(form_data)
    response = await parse_response_for_triggered_analysis(response, container, db, "static")

    if response.status_code == 200: 
        await update_container_status(STATUS.ACTIVE.value, container, db)

    return response

@router.post("/analysis/network")
async def start_static_container_analysis(network_analysis_data: NetworkAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, network_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return Response(content=f"container with id {container.id} is not Idle!, aborting", status_code=500) 
    
    data = json.dumps(network_analysis_data.__dict__)
    response: HTTPResponse = await container.start_network_analysis(data)
    response = await parse_response_for_triggered_analysis(response, container, db, "network")
    # set container status to active/idle afterwards before
    if response.status_code == 200:
        await update_container_status(STATUS.ACTIVE.value, container, db)
    
    return response

@router.post("/analysis/stop")
async def stop_analysis(stop_data: StopAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, stop_data.container_id)
    response: HTTPResponse = await container.stop_analysis()
    # set container status to active/idle afterwards before
    if response.status_code == 200:
        await update_container_status(STATUS.IDLE.value, container, db)
        message = f"Analysis for container {container.id} stopped successfully"
        return create_response_message(message, 200)
    else:
        message = f"Analysis for container {container.id} did not stop successfully"
        return create_response_error(message, 500)

# Endpoint to receive notice when triggered analysis (static) has finished
@router.post("/analysis/finished")
async def finished_analysis(analysisFinishedData: AnalysisFinishedData, db=Depends(get_db)):
    container = get_container_by_id(db, analysisFinishedData.container_id)
    await update_container_status(STATUS.IDLE.value, container, db)
    return Response(content=f"Successfully stopped analysis for fontainer {analysisFinishedData.container_id}", status_code=200)


@router.post("/publish/alerts")
async def receive_alerts_from_ids(alert_data: AlertData, db=Depends(get_db), background_tasks: BackgroundTasks = BackgroundTasks()):
    container = get_container_by_id(db, alert_data.container_id)
    labels = {
        "container_name": container.name,
        "analysis_type": alert_data.analysis_type,
        "ensemble": "None",
        "ensemble_analysis_id": "None",
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
        background_tasks.add_task(calculate_evaluation_metrics_and_push, dataset=dataset, alerts=alerts, container_name=container.name)
    background_tasks.add_task(push_alerts_to_loki, alerts=alerts, labels=labels)
    return Response(content=f"Successfully pushed alerts and metrics to Loki", status_code=200)
