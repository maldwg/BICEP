import logging
from http.client import HTTPResponse
from app.models.benchmarking import BenchmarkingResultTransferObject
from fastapi import APIRouter, Depends, Response, BackgroundTasks
from app.validation.models import (
    AlertData,
    IdsContainerCreate,
    NetworkAnalysisData,
    StaticAnalysisData,
    stop_analysisData,
    AnalysisFinishedData,
)
from app.models.ids_system import (
    IdsSystem,
    build_ids_system_name,
    get_ids_system_by_id,
    get_ids_system_by_id_any_status,
    get_ids_system_model,
    update_ids_status,
)
from app.models.configuration import get_config_by_id
from app.models.dataset import Dataset, get_dataset_by_id
from app.utils import (
    DOCKER_HOST_STATUS,
    DEPLOYMENT_STATUS,
    finish_ids_setup,
    create_response_error,
    create_response_message,
    find_free_port,
    STATUS,
    parse_response_for_triggered_analysis,
    calculate_evaluation_metrics_and_push,
)
from app.loki import push_alerts_to_loki
from app.bicep_utils.models.ids_base import Alert
from app.models.docker_host_system import get_host_by_id
from fastapi.responses import JSONResponse
from app.database import get_db
from datetime import datetime
from app.models.ids_tool import get_ids_by_id
from app.models.ensemble import get_ensemble_by_id
from app.prometheus import build_resource_query_spec_for_ids_system


logger = logging.getLogger('bicep.ids')

router = APIRouter(prefix="/ids")

@router.post("/setup")
async def setup_ids(
    data: IdsContainerCreate,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    host = await get_host_by_id(db, data.host_system_id)
    if host.status == DOCKER_HOST_STATUS.UNAVAILABLE.value:
        return JSONResponse(
            {"message": "The specified host is unavailable, try another!"},
            status_code=500,
        )

    # Look up the tool to determine the correct IDS system subclass

    ids_tool = await get_ids_by_id(db, data.ids_tool_id)
    if not ids_tool:
        return JSONResponse(
            {"message": "IDS Tool not found"},
            status_code=404,
        )

    free_port = find_free_port()
    ruleset_id = data.ruleset_id if data.ruleset_id else None
    initial_name = build_ids_system_name(ids_tool.name, free_port)

    ids_system_model = get_ids_system_model(getattr(ids_tool, "ids_type", None))
    ids_system: IdsSystem = ids_system_model(
        name=initial_name,
        host_system_id=host.id,
        port=free_port,
        description=data.description,
        configuration_id=data.configuration_id,
        ids_tool_id=data.ids_tool_id,
        status=STATUS.SETTING_UP.value,
        deployment_status=DEPLOYMENT_STATUS.DEPLOYED.value,
        ruleset_id=ruleset_id,
    )

    db.add(ids_system)
    await db.commit()
    await db.refresh(ids_system)

    background_tasks.add_task(
        finish_ids_setup,
        ids_system.id,
        data.cids_configurations or [],
        data.env_vars or {},
    )

    return JSONResponse(
        content={"message": "setup started", "container_id": ids_system.id},
        status_code=202,
        background=background_tasks,
    )


@router.delete("/remove/{container_id}")
async def remove_container(container_id: int, db=Depends(get_db)):
    container: IdsSystem = await get_ids_system_by_id_any_status(db, container_id)
    if container is None:
        return JSONResponse(
            {"error": f"container with id {container_id} was not found"},
            status_code=404,
        )
    if container.status == STATUS.SETTING_UP.value:
        return JSONResponse(
            {
                "error": (
                    f"container with id {container_id} is still setting up and "
                    "cannot be deleted yet"
                )
            },
            status_code=409,
        )
    if container.deployment_status == DEPLOYMENT_STATUS.DELETED.value:
        return Response(status_code=204)
    try:
        # stop analysis to also remove interfaces created if run in networking mode
        await container.stop_analysis()
    except Exception as exc:
        logger.warning(f"Failed to stop analysis before teardown of {container.name}: {exc}")
    await container.teardown(db)
    return Response(status_code=204)


@router.post("/analysis/static")
async def start_static_container_analysis(
    static_analysis_data: StaticAnalysisData, db=Depends(get_db)
):
    ids: IdsSystem = await get_ids_system_by_id(
        db, static_analysis_data.container_id
    )
    if ids is None:
        return JSONResponse(
            {
                "error": f"container with id {static_analysis_data.container_id} was not found"
            },
            status_code=404,
        )
    if ids.ensemble_ids != []:
        return JSONResponse(
            {
                "error": f"container with id {ids.id} is part of an ensemble. Hence, no individual analysis is possible"
            },
            status_code=500,
        )

    if ids.status != STATUS.IDLE.value:
        return JSONResponse(
            {"error": f"container with id {ids.id} is not Idle!, aborting"},
            status_code=500,
        )

    if not await ids.is_available(db):
        return JSONResponse(
            {
                "error": f"container with id {ids.id} is not available! Check if it should be deleted"
            },
            status_code=500,
        )

    dataset: Dataset = await get_dataset_by_id(db, static_analysis_data.dataset_id)
    await update_ids_status(db, STATUS.ACTIVE.value, ids)
    form_data = {
        "container_id": (None, str(ids.id), "application/json"),
        # "dataset": (dataset.name, data_file, "application/octet-stream"),
        "dataset_id": (None, str(dataset.id), "application/json"),
    }
    try:
        response: HTTPResponse = await ids.start_static_analysis(form_data, dataset)
        response = await parse_response_for_triggered_analysis(
            response, ids, "static"
        )
        # set container status to IDLE if request failed
        if response.status_code != 200:
            await update_ids_status(db, STATUS.IDLE.value, ids)

        return response
    except Exception as e:
        await update_ids_status(db, STATUS.IDLE.value, ids)
        logger.error(f"Failed to start static analysis: {e}")
        return create_response_error(f"Failed to start static analysis: {e}", 500)


@router.post("/analysis/network")
async def start_network_container_analysis(
    network_analysis_data: NetworkAnalysisData, db=Depends(get_db)
):
    ids: IdsSystem = await get_ids_system_by_id(
        db, network_analysis_data.container_id
    )
    if ids is None:
        return JSONResponse(
            {
                "error": f"container with id {network_analysis_data.container_id} was not found"
            },
            status_code=404,
        )

    if ids.ensemble_ids != []:
        return JSONResponse(
            {
                "error": f"container with id {ids.id} is part of an ensemble. Hence, no individual analysis is possible"
            },
            status_code=500,
        )

    if ids.status != STATUS.IDLE.value:
        return JSONResponse(
            {"error": f"container with id {ids.id} is not Idle!, aborting"},
            status_code=500,
        )

    if not await ids.is_available(db):
        return JSONResponse(
            {
                "error": f"container with id {ids.id} is not available! Check if it should be deleted"
            },
            status_code=500,
        )

    data = network_analysis_data.__dict__
    await update_ids_status(db, STATUS.ACTIVE.value, ids)
    try:
        response: HTTPResponse = await ids.start_network_analysis(data)
        timestamp = datetime.now().isoformat()
        logger.info(
            f"Started network analysis for container{ids.name} at {timestamp}"
        )
        response = await parse_response_for_triggered_analysis(
            response, ids, "network"
        )
        # set container status to IDLE if request failed
        if response.status_code != 200:
            await update_ids_status(db, STATUS.IDLE.value, ids)

        return response
    except Exception as e:
        await update_ids_status(db, STATUS.IDLE.value, ids)
        logger.error(f"Failed to start network analysis: {e}")
        return create_response_error(f"Failed to start network analysis: {e}", 500)


@router.post("/analysis/stop")
async def stop_analysis(stop_data: stop_analysisData, db=Depends(get_db)):
    container: IdsSystem = await get_ids_system_by_id(db, stop_data.container_id)
    if container is None:
        return JSONResponse(
            {"error": f"container with id {stop_data.container_id} was not found"},
            status_code=404,
        )
    # check if container is part of an ensemble to prevent stopping an ensemble container individually
    if container.ensemble_ids != []:
        for ensemble_ids_of_container in container.ensemble_ids:
            ensemble_id = ensemble_ids_of_container.ensemble_id
            ensemble = await get_ensemble_by_id(db, ensemble_id)
            if ensemble.status == STATUS.ACTIVE.value:
                message = f"Container is part of a running ensemble. It is not possible to stop a container analysis individually"
                return create_response_error(message, 500)
    response: HTTPResponse = await container.stop_analysis()
    # set container status to active/idle afterwards before
    if response.status_code == 200:
        await update_ids_status(db, STATUS.IDLE.value, container)
        message = f"Analysis for container {container.id} stopped successfully"
        return create_response_message(message, 200)
    else:
        message = f"Analysis for container {container.id} did not stop successfully"
        return create_response_error(message, 500)


# Endpoint to receive notice when triggered analysis (static) has finished
@router.post("/analysis/finished")
async def finished_analysis(
    analysisFinishedData: AnalysisFinishedData, db=Depends(get_db)
):
    container = await get_ids_system_by_id_any_status(db, analysisFinishedData.container_id)
    if container is None:
        return JSONResponse(
            {
                "error": f"container with id {analysisFinishedData.container_id} was not found"
            },
            status_code=404,
        )
    await update_ids_status(db, STATUS.IDLE.value, container)
    return JSONResponse(
        {"message": f"Successfully stopped analysis for container {container.name}"},
        status_code=200,
    )


@router.post("/publish/alerts")
async def receive_alerts_from_ids(
    alert_data: AlertData, background_tasks: BackgroundTasks, db=Depends(get_db)
):
    container = await get_ids_system_by_id_any_status(db, alert_data.container_id)
    if container is None:
        return JSONResponse(
            {"error": f"container with id {alert_data.container_id} was not found"},
            status_code=404,
        )
    logger.debug(f"analysis-type: {alert_data.analysis_type}")
    logger.debug(f"Received Logs for container {container.name}")
    labels = {
        "container_name": container.name,
        "analysis_type": alert_data.analysis_type,
        "ensemble": "None",
        "ensemble_analysis_id": "None",
        "logging": "alerts",
    }
    if alert_data.dataset_id != None:
        dataset = await get_dataset_by_id(db, dataset_id=alert_data.dataset_id)
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
    logger.debug(f"Created {len(alerts)} alerts")
    background_tasks.add_task(push_alerts_to_loki, alerts, labels)
    if alert_data.analysis_type == "static":
        resource_query_mode, resource_query_targets = (
            build_resource_query_spec_for_ids_system(container)
        )
        # Fetch configuration and ruleset names
        configuration = await get_config_by_id(db, container.configuration_id)
        configuration_name = configuration.name if configuration else None
        ruleset_name = None
        if container.ruleset_id:
            ruleset = await get_config_by_id(db, container.ruleset_id)
            ruleset_name = ruleset.name if ruleset else None

        benchmarking_results = BenchmarkingResultTransferObject(
            alerts=alerts,
            dataset_id=alert_data.dataset_id,
            start_time=alert_data.start_time,
            stop_time=alert_data.stop_time,
        )
        background_tasks.add_task(
            calculate_evaluation_metrics_and_push,
            db=db,
            benchmarking_results=benchmarking_results,
            container_name=container.name,
            configuration_name=configuration_name,
            ruleset_name=ruleset_name,
            resource_query_mode=resource_query_mode,
            resource_query_targets=resource_query_targets,
        )
    return JSONResponse(
        {"content": f"Successfully pushed alerts and metrics to Loki"}, status_code=200
    )
