import asyncio
from http.client import HTTPResponse
from fastapi import APIRouter, Depends, Response, BackgroundTasks
from ..database import get_db
from ..validation.models import AlertData, IdsContainerCreate, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, stop_analysisData, AnalysisFinishedData
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status, get_all_container
from ..models.configuration import Configuration, get_config_by_id
from ..models.dataset import Dataset, get_dataset_by_id
from ..utils import get_background_tasks,get_stream_metric_tasks ,create_response_error, create_response_message, find_free_port, STATUS, parse_response_for_triggered_analysis, calculate_evaluation_metrics_and_push
import httpx 
import json 
from fastapi.encoders import jsonable_encoder
from ..prometheus import push_evaluation_metrics_to_prometheus
from ..metrics import calculate_evaluation_metrics
from ..loki import push_alerts_to_loki
from ..bicep_utils.models.ids_base import Alert
from ..models.docker_host_system import get_host_by_id
from fastapi.responses import JSONResponse
from ..logger import LOGGER

router = APIRouter(
    prefix="/ids"
)

@router.post("/setup")
async def setup_ids(data: IdsContainerCreate, db=Depends(get_db), stream_metric_tasks=Depends(get_stream_metric_tasks)):
    host = get_host_by_id(data.host_system_id, db=db)

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
    await ids_container.setup(db)
    await ids_container.start_metric_collection(db=db, stream_metric_tasks=stream_metric_tasks)
    return JSONResponse(content={"message": "setup done"}, status_code=200)


@router.delete("/remove/{container_id}")
async def remove_container(container_id: int, db=Depends(get_db), stream_metric_tasks=Depends(get_stream_metric_tasks)):
    container: IdsContainer = get_container_by_id(db, container_id)
    try:
        print("test")
        await container.stop_metric_collection(db=db, stream_metric_tasks=stream_metric_tasks)
        print("stopped metrics")
        # stop analysis to also remove interfaces created if run in networking mode
        await container.stop_analysis()
        print("stopped container analysis")
    except Exception as e:
        print(e)
    await container.teardown(db)
    print("teared down")
    return Response(status_code=204)

@router.post("/analysis/static")
async def start_static_container_analysis(static_analysis_data: StaticAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, static_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return JSONResponse({"content": f"container with id {container.id} is not Idle!, aborting"}, status_code=500)
    
    print(await container.is_available())
    if not await container.is_available():
         return JSONResponse({"content": f"container with id {container.id} is not available! Check if it should be deleted"}, status_code=500)


    dataset: Dataset = get_dataset_by_id(db, static_analysis_data.dataset_id)
    await update_container_status(STATUS.ACTIVE.value, container, db)
    # pcap_file = await dataset.read_pcap_file()
    form_data= {
            "container_id": (None, str(container.id), "application/json"),
            # "dataset": (dataset.name, pcap_file, "application/octet-stream"),
            "dataset_id": (None, str(dataset.id), "application/json")
        }    
    response: HTTPResponse = await container.start_static_analysis(form_data, dataset)
    response = await parse_response_for_triggered_analysis(response, container, db, "static")
    # set container status to IDLE if request failed
    if response.status_code != 200: 
        await update_container_status(STATUS.IDLE.value, container, db)

    return response

@router.post("/analysis/network")
async def start_network_container_analysis(network_analysis_data: NetworkAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, network_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return JSONResponse({"content": f"container with id {container.id} is not Idle!, aborting"}, status_code=500) 
    

    if not await container.is_available():
         return JSONResponse({"content": f"container with id {container.id} is not available! Check if it should be deleted"}, status_code=500)


    data = json.dumps(network_analysis_data.__dict__)
    await update_container_status(STATUS.ACTIVE.value, container, db)
    response: HTTPResponse = await container.start_network_analysis(data)
    response = await parse_response_for_triggered_analysis(response, container, db, "network")
    # set container status to IDLE if request failed
    if response.status_code != 200:
        await update_container_status(STATUS.IDLE.value, container, db)
    
    return response

@router.post("/analysis/stop")
async def stop_analysis(stop_data: stop_analysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, stop_data.container_id)
    response: HTTPResponse = await container.stop_analysis()
    print(response)
    # set container status to active/idle afterwards before
    if response.status_code == 200:
        await update_container_status(STATUS.IDLE.value, container, db)
        print(container.status)
        message = f"Analysis for container {container.id} stopped successfully"
        print(message)
        return create_response_message(message, 200)
    else:
        print("500")
        message = f"Analysis for container {container.id} did not stop successfully"
        print(message)
        return create_response_error(message, 500)

# Endpoint to receive notice when triggered analysis (static) has finished
@router.post("/analysis/finished")
async def finished_analysis(analysisFinishedData: AnalysisFinishedData, db=Depends(get_db)):
    container = get_container_by_id(db, analysisFinishedData.container_id)
    await update_container_status(STATUS.IDLE.value, container, db)
    print(f"Updated status of {container.name} to IDLE")
    return JSONResponse({"message": f"Successfully stopped analysis for container {container.name}"}, status_code=200)


@router.post("/publish/alerts")
async def receive_alerts_from_ids(alert_data: AlertData, db=Depends(get_db), background_tasks=Depends(get_background_tasks)):
    container = get_container_by_id(db, alert_data.container_id)
    print(f"Received Logs for container {container.name}")
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
    print(alert_data.alerts[0:2])
    print("test")
    print(f"recievd {len(alerts)} alerts")
    send_task = asyncio.create_task(push_alerts_to_loki(alerts=alerts, labels=labels))
    background_tasks.add(send_task)
    print(f"analysis-type: {alert_data.analysis_type}")
    if alert_data.analysis_type == "static":
        calc_task = asyncio.create_task(calculate_evaluation_metrics_and_push(dataset=dataset, alerts=alerts, container_name=container.name))
        background_tasks.add(calc_task)
    return JSONResponse({"content": f"Successfully pushed alerts and metrics to Loki"}, status_code=200)


@router.get("/help/background-tasks")
async def display_background_tasks(background_tasks=Depends(get_background_tasks)):
    for t in background_tasks:
        print(t)


@router.get("/help/metrics")
async def display_metric_tasks(db=Depends(get_db), stream_metric_tasks=Depends(get_stream_metric_tasks)):
    print(stream_metric_tasks)
    containers: list[IdsContainer] = get_all_container(db=db)
    for container in containers:
        print(container.name)
        print(container.stream_metric_task_id)
        try:
            task = stream_metric_tasks[container.stream_metric_task_id]
            print(task)
        except:
            print("Exce")
