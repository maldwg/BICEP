from http.client import HTTPResponse
from fastapi import APIRouter, Depends, Response
from ..dependencies import get_db
from ..validation.models import IdsContainerCreate, EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, StopAnalysisData
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from ..models.configuration import Configuration, get_config_by_id
from ..utils import find_free_port, STATUS, get_container_host
import httpx 
import json 
from fastapi.encoders import jsonable_encoder


router = APIRouter(
    prefix="/ids"
)

# TODO: docker needs longer or cant take it at all when image needs to be pulled. solution ?

@router.post("/setup")
async def setup_ids(data: IdsContainerCreate, db=Depends(get_db)):
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
    return {"message": "setup done"}


@router.delete("/remove/{container_id}")
async def remove_container(container_id: int, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, container_id)
    await container.teardown(db)
    return {"message": "teardown done"}

@router.post("/analysis/static")
async def start_static_container_analysis(static_analysis_data: StaticAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, static_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return Response(content=f"container with id {container.id} is not Idle!, aborting", status_code=500)

    dataset: Configuration = get_config_by_id(db, static_analysis_data.dataset_id)
    host = get_container_host(container)
    container_url = f"http://{host}:{container.port}"
    endpoint = "/analysis/static"
    await update_container_status(STATUS.ACTIVE.value, container, db)
    async with httpx.AsyncClient() as client:
        form_data= {
            "container_id": (None, str(container.id), "application/json"),
            "file": (dataset.name, dataset.configuration, "application/octet-stream"),
        }    
        response: HTTPResponse = await client.post(container_url+endpoint,files=form_data)
    if response.status_code == 200: 
        return {"message": f"static analysis for ids triggered {static_analysis_data},  response = {response}"}
    else:
        return {"message": f"static analysis for ids could not be triggered {static_analysis_data},  response = {response}"}

@router.post("/analysis/network")
async def start_static_container_analysis(network_analysis_data: NetworkAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, network_analysis_data.container_id)

    if container.status != STATUS.IDLE.value:
        return Response(content=f"container with id {container.id} is not Idle!, aborting", status_code=500)

    host = get_container_host(container)
    container_url = f"http://{host}:{container.port}"
    endpoint = "/analysis/network"
    async with httpx.AsyncClient() as client:
        response = await client.post(container_url+endpoint, data=json.dumps(network_analysis_data.__dict__))
    # set container status to active/idle afterwards before
    if response.status_code == 200:
        await update_container_status(STATUS.ACTIVE.value, container, db)
        return {"message": f"static analysis for ids triggered {network_analysis_data},  response = {response}"}
    else:
        return {"message": f"network analysis for ids could not be triggered {network_analysis_data},  response = {response}"}

@router.post("/analysis/stop")
async def stop_analysis(stop_data: StopAnalysisData, db=Depends(get_db)):
    container: IdsContainer = get_container_by_id(db, stop_data.container_id)
    host = get_container_host(container)
    container_url = f"http://{host}:{container.port}"
    endpoint = "/analysis/stop"
    async with httpx.AsyncClient() as client:
        response = await client.post(container_url+endpoint)
    # set container status to active/idle afterwards before
    await update_container_status(STATUS.IDLE.value, container, db)
    return {"message": f"successfully stopped analysis for container {stop_data}, response = {response}"}


@router.post("/analysis/finished/{container_id}")
async def finished_analysis(container_id: int, db=Depends(get_db)):
    container = get_container_by_id(db, container_id)
    await update_container_status(STATUS.IDLE.value, container, db)
    return Response(content=f"Successfully stopped analysis for fontainer {container_id}", status_code=200)