import asyncio
from http.client import HTTPResponse
from fastapi import APIRouter, Depends, Response, BackgroundTasks
from ..validation.models import AlertData, IdsContainerCreate, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, stop_analysisData, AnalysisFinishedData
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status, get_all_container
from ..models.configuration import Configuration, get_config_by_id
from ..models.dataset import Dataset, get_dataset_by_id
from ..utils import get_stream_metric_tasks ,create_response_error, create_response_message, find_free_port, STATUS, parse_response_for_triggered_analysis, calculate_evaluation_metrics_and_push
import httpx 
import json 
from fastapi.encoders import jsonable_encoder
from ..loki import push_alerts_to_loki
from ..bicep_utils.models.ids_base import Alert
from ..models.docker_host_system import get_host_by_id
from fastapi.responses import JSONResponse
from ..logger import LOGGER

router = APIRouter(
    prefix="/ids"
)

@router.post("/setup")
async def setup_ids(data: IdsContainerCreate, stream_metric_tasks=Depends(get_stream_metric_tasks)):
    host = await get_host_by_id(data.host_system_id)

    free_port=find_free_port()
    if data.ruleset_id:
        ruleset_id = data.ruleset_id
    else:
        ruleset_id = None
    ids_container = IdsContainer(
        host_system_id=host.id,
        port=free_port,
        description=data.description,
        configuration_id=data.configuration_id,
        ids_tool_id=data.ids_tool_id,
        status=STATUS.ACTIVE.value,
        ruleset_id=ruleset_id
        )
    await ids_container.setup()
    await ids_container.start_metric_collection(stream_metric_tasks=stream_metric_tasks)
    return JSONResponse(content={"message": "setup done"}, status_code=200)


@router.delete("/remove/{container_id}")
async def remove_container(container_id: int, stream_metric_tasks=Depends(get_stream_metric_tasks)):
    container: IdsContainer = await get_container_by_id(container_id)
    try:
        await container.stop_metric_collection(stream_metric_tasks=stream_metric_tasks)
        # stop analysis to also remove interfaces created if run in networking mode
        await container.stop_analysis()
        LOGGER.debug("stopped container analysis")
    except Exception as e:
        print(e)
    await container.teardown()
    return Response(status_code=204)

@router.post("/analysis/static")
async def start_static_container_analysis(static_analysis_data: StaticAnalysisData):
    container: IdsContainer = await get_container_by_id(static_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return JSONResponse({"error": f"container with id {container.id} is not Idle!, aborting"}, status_code=500)
    
    print(await container.is_available())
    if not await container.is_available():
         return JSONResponse({"error": f"container with id {container.id} is not available! Check if it should be deleted"}, status_code=500)


    dataset: Dataset = await get_dataset_by_id(static_analysis_data.dataset_id)
    await update_container_status(STATUS.ACTIVE.value, container)
    # data_file = await dataset.read_data_file()
    form_data= {
            "container_id": (None, str(container.id), "application/json"),
            # "dataset": (dataset.name, data_file, "application/octet-stream"),
            "dataset_id": (None, str(dataset.id), "application/json")
        }    
    response: HTTPResponse = await container.start_static_analysis(form_data, dataset)
    response = await parse_response_for_triggered_analysis(response, container, "static")
    # set container status to IDLE if request failed
    if response.status_code != 200: 
        await update_container_status(STATUS.IDLE.value, container)

    return response

@router.post("/analysis/network")
async def start_network_container_analysis(network_analysis_data: NetworkAnalysisData):
    container: IdsContainer = await get_container_by_id(network_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return JSONResponse({"error": f"container with id {container.id} is not Idle!, aborting"}, status_code=500) 
    

    if not await container.is_available():
         return JSONResponse({"error": f"container with id {container.id} is not available! Check if it should be deleted"}, status_code=500)


    data = json.dumps(network_analysis_data.__dict__)
    await update_container_status(STATUS.ACTIVE.value, container)
    response: HTTPResponse = await container.start_network_analysis(data)
    response = await parse_response_for_triggered_analysis(response, container, "network")
    # set container status to IDLE if request failed
    if response.status_code != 200:
        await update_container_status(STATUS.IDLE.value, container)
    
    return response

@router.post("/analysis/stop")
async def stop_analysis(stop_data: stop_analysisData):
    container: IdsContainer = await get_container_by_id(stop_data.container_id)
    if container.ensemble_ids != []:
        for ensemble_ids_of_container in container.ensemble_ids:
            ensemble = ensemble_ids_of_container.ensemble
            if ensemble.status == STATUS.ACTIVE.value:
                message = f"Container is part of a running ensemble. It is not possible to stop a container analysis individually"
                return create_response_error(message, 500)
    response: HTTPResponse = await container.stop_analysis()
    # set container status to active/idle afterwards before
    if response.status_code == 200:
        await update_container_status(STATUS.IDLE.value, container)
        message = f"Analysis for container {container.id} stopped successfully"
        return create_response_message(message, 200)
    else:
        message = f"Analysis for container {container.id} did not stop successfully"
        return create_response_error(message, 500)

# Endpoint to receive notice when triggered analysis (static) has finished
@router.post("/analysis/finished")
async def finished_analysis(analysisFinishedData: AnalysisFinishedData):
    container = await get_container_by_id(analysisFinishedData.container_id)
    await update_container_status(STATUS.IDLE.value, container)
    return JSONResponse({"message": f"Successfully stopped analysis for container {container.name}"}, status_code=200)


@router.post("/publish/alerts")
async def receive_alerts_from_ids(alert_data: AlertData, background_tasks: BackgroundTasks):
    container = await get_container_by_id(alert_data.container_id)
    LOGGER.debug(f"analysis-type: {alert_data.analysis_type}")
    LOGGER.debug(f"Received Logs for container {container.name}")
    labels = {
        "container_name": container.name,
        "analysis_type": alert_data.analysis_type,
        "ensemble": "None",
        "ensemble_analysis_id": "None",
        "logging": "alerts",
    }
    if alert_data.dataset_id != None:
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
    LOGGER.debug(f"Created {len(alerts)} alerts")
    background_tasks.add_task(push_alerts_to_loki, alerts, labels)
    if alert_data.analysis_type == "static":
        background_tasks.add_task(calculate_evaluation_metrics_and_push, dataset=dataset, alerts=alerts,container_name=container.name)
    return JSONResponse({"content": f"Successfully pushed alerts and metrics to Loki"}, status_code=200)
