from http.client import HTTPResponse
import json
from ..models.configuration import Configuration, get_config_by_id
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from fastapi import APIRouter, Depends, Response
from ..dependencies import get_db
from ..validation.models import EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, StopAnalysisData
from ..models.ensemble import get_all_ids_ensembles, Ensemble, add_ensemble, get_ensemble_by_id, remove_ensemble, update_ensemble_status
import httpx 
from ..utils import find_free_port, STATUS, get_container_host

router = APIRouter(
    prefix="/ensemble"
)

#TODO: REMOVE db from setup methods for ids and ensemble

@router.post("/setup")
async def setup_ensembles(ensembleData: EnsembleCreate,db=Depends(get_db)):
    ensemble = Ensemble(
        name=ensembleData.name,
        description=ensembleData.description, 
        technique_id=ensembleData.technique,
        status=STATUS.IDLE.value)
    await add_ensemble(ensemble, db)
    for id in ensembleData.container_ids:
        ensemble.add_container(id, db)
    return {"message": "successfully setup ensemble "}

@router.delete("/remove/{ensemble_id}")
async def setup_ensembles(ensemble_id: int,db=Depends(get_db)):
    ensemble = get_ensemble_by_id(ensemble_id, db)
    remove_ensemble(ensemble, db)
    return {"message": "successfully removed ensemble "}


@router.post("/analysis/static")
async def start_static_container_analysis(static_analysis_data: StaticAnalysisData, db=Depends(get_db)):
    dataset: Configuration = get_config_by_id(db, static_analysis_data.dataset_id)
    
    ensemble: Ensemble = get_ensemble_by_id(static_analysis_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    response = {}

    endpoint = "/analysis/static"
    for container in containers:
        static_analysis_data.container_id = container.id
        host = get_container_host(container)
        container_url = f"http://{host}:{container.port}"
        async with httpx.AsyncClient() as client:
                form_data= {
                    "container_id": (None, str(container.id), "application/json"),
                    "ensemble_id": (None, str(ensemble.id), "application/json"),
                    "file": (dataset.name, dataset.configuration, "application/octet-stream"),
                }    
                response: HTTPResponse = await client.post(container_url+endpoint,files=form_data)
            # set container status to active/idle afterwards before
        if response.status_code == 200:
            await update_container_status(STATUS.ACTIVE.value, container, db)
            response.update({f"container {static_analysis_data.container_id}": f"static analysis for ensemble {ensemble.id} and ids {static_analysis_data.container_id} triggered,  response = {response}"})
        else:
             response.update({f"container {static_analysis_data.container_id}": f"static analysis for ensemble {ensemble.id} and ids {static_analysis_data.container_id} could not be triggered,  response = {response}"})    
    return response

# TODO: status ausbauen (bspw. ensemble active hinzufügen damit man sieht dass ei ids von einem ensemble gestartet wurde. Ansonsten keine ,öglichkeit das per GUI heruszufinden)

@router.post("/analysis/network")
async def start_static_container_analysis(network_analysis_data: NetworkAnalysisData, db = Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(network_analysis_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    response = {}

    endpoint = "/analysis/network"
    for container in containers:
        network_analysis_data.container_id = container.id
        host = get_container_host(container)
        container_url = f"http://{host}:{container.port}"
        async with httpx.AsyncClient() as client:
                response: HTTPResponse = await client.post(container_url+endpoint, data=json.dumps(network_analysis_data.__dict__))
        # set container status to active/idle afterwards before
        if response.status_code == 200:
            await update_container_status(STATUS.ACTIVE.value, container, db)
            response.update({f"container {network_analysis_data.container_id}": f"static analysis for ensemble {ensemble.id} and ids {network_analysis_data.container_id} triggered,  response = {response}"})
        else:
            response.update({f"container {network_analysis_data.container_id}": f"static analysis for ensemble {ensemble.id} and ids {network_analysis_data.container_id} could not be triggered,  response = {response}"})    
    return response



@router.post("/analysis/stop")
async def stop_analysis(stop_data: StopAnalysisData):
    return {"message": f"successfully stopped analysis for ensemble {stop_data}"}



@router.post("/analysis/stop")
async def stop_analysis(stop_data: StopAnalysisData, db=Depends(get_db)):
    ensemble: Ensemble = get_ensemble_by_id(stop_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    responses = {}

    for container in containers:
        host = get_container_host(container)
        container_url = f"http://{host}:{container.port}"
        endpoint = "/analysis/stop"
        async with httpx.AsyncClient() as client:
            response = await client.post(container_url+endpoint)
        # set container status to active/idle afterwards before
        if response.status_code == 200:
            await update_container_status(STATUS.IDLE.value, container, db)
            responses.update({f"container {container.id}": f"Stopped analysis for container {container.id} in ensemble {ensemble.id}, response = {response}"})
        else:
            responses.update({f"container {container.id}": f"Could not stop analysis for container {container.id} in ensemble {ensemble.id}, response = {response}"})
    
    return responses


@router.post("{ensemble_id}/analysis/finished/{container_id}")
async def finished_analysis(ensemble_id: int, container_id: int, db=Depends(get_db)):
    container = get_container_by_id(db, container_id)
    ensemble = get_ensemble_by_id(db, ensemble_id)
    await update_container_status(STATUS.IDLE.value, container, db)
    await update_ensemble_status(STATUS.IDLE.value, ensemble, db)
    return Response(content=f"Successfully stopped analysis for esemble {ensemble_id} and container {container_id}", status_code=200)