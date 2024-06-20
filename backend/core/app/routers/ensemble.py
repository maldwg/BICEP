from http.client import HTTPResponse
import json

from ..models.ensemble_ids import get_all_ensemble_container, EnsembleIds
from ..models.configuration import Configuration, get_config_by_id
from ..models.ids_container import IdsContainer, get_container_by_id, update_container_status
from fastapi import APIRouter, Depends, Response
from fastapi.encoders import jsonable_encoder
from ..dependencies import get_db
from ..validation.models import EnsembleCreate, NetworkAnalysisData, StaticAnalysisData, StopAnalysisData
from ..models.ensemble import get_all_ensembles, Ensemble, add_ensemble, get_ensemble_by_id, remove_ensemble, update_ensemble_status
import httpx 
from ..utils import deregister_container_from_ensemble, find_free_port, STATUS, get_container_host, create_response_error, create_response_message, create_generic_response_message_for_ensemble
from fastapi.responses import JSONResponse

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
async def setup_ensembles(ensemble_id: int,db=Depends(get_db)):
    ensemble = get_ensemble_by_id(ensemble_id, db)
    ids_ensembles: list[EnsembleIds] = get_all_ensemble_container(db)
    container_id_list = [ids_ensemble.ids_container_id  for ids_ensemble in ids_ensembles if ids_ensemble.ensemble_id == ensemble_id]
    container_list = [ get_container_by_id(db=db, id=id) for id in container_id_list]
     
    responses = []
    for container in container_list:
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
    dataset: Configuration = get_config_by_id(db, static_analysis_data.dataset_id)
    
    ensemble: Ensemble = get_ensemble_by_id(static_analysis_data.ensemble_id, db)
    containers: list[IdsContainer] = ensemble.get_containers(db)

    for container in containers:
        if container.status != STATUS.IDLE.value:
            message = f"container with id {container.id} is not Idle!, aborting"
            return create_response_error(message, 500)

    responses: list[HTTPResponse] = await ensemble.start_static_analysis(dataset, static_analysis_data, db)
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
        response: HTTPResponse = await container.stop_analysis()
        
        if response.status_code == 200:
            await update_container_status(STATUS.IDLE.value, container, db)
            message = f"Successfully stopped analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 200))
        else:
            message = f"Could not stop analysis for container {container.id} and ensemble {ensemble.id}"
            responses.append(create_generic_response_message_for_ensemble(message, 500))
    await update_ensemble_status(db=db, ensemble=ensemble, status=STATUS.IDLE.value)
    return JSONResponse(content={"content": responses}, status_code=200)

@router.post("/{ensemble_id}/analysis/finished/{container_id}")
async def finished_analysis(ensemble_id: int, container_id: int, db=Depends(get_db)):
    container = get_container_by_id(db, container_id)
    ensemble = get_ensemble_by_id(ensemble_id, db)
    await update_container_status(STATUS.IDLE.value, container, db)
    await update_ensemble_status(STATUS.IDLE.value, ensemble, db)
    return Response(content=f"Successfully finished analysis for esemble {ensemble_id} and container {container_id}", status_code=200)