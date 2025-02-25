import base64
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from ..models.configuration import get_all_configurations, remove_configuration_by_id, add_config,Configuration, get_all_configurations_by_type
from ..models.dataset import Dataset, get_all_datasets, remove_dataset_by_id
from ..models.ids_tool import get_all_tools
from ..models.ids_container import get_all_container, update_container
from ..models.ensemble import get_all_ensembles, update_ensemble
from ..models.ensemble_technique import get_all_ensemble_techniques
from ..models.ensemble_ids import get_all_ensemble_container
from ..utils import FILE_TYPES, get_serialized_confgigurations, calculate_and_add_dataset, file_type_is_accepted
from ..validation.models import EnsembleUpdate, IdsContainerUpdate, DockerHostCreationData
from ..models.docker_host_system import get_all_hosts, remove_host, add_host_system, DockerHostSystem
from ..models.dataset_types import get_dataset_type_by_id, get_all_dataset_types
from ..logger import LOGGER

router = APIRouter(
    prefix="/crud"
)



@router.get("/configuration/all")
async def get_all_configs():
    configurations = await get_all_configurations()
    serialized_configurations = get_serialized_confgigurations(configurations)
    return serialized_configurations

@router.get("/configuration/file-types")
async def get_all_config_filetypes():
    types = [t.value for t in FILE_TYPES]
    return types


@router.get("/configuration/all/{file_type}")
async def get_all_configs_of_a_filetype(file_type: str):
    valid_file_types = [t.value for t in FILE_TYPES]
    if file_type in valid_file_types:
        configurations = await get_all_configurations_by_type(file_type)
        serialized_configurations = get_serialized_confgigurations(configurations)
        return serialized_configurations
    else:
        return {"error": "wrong file type"}

@router.delete("/configuration/{id}")
async def remove_config( id: int):
    await remove_configuration_by_id(id)
    return Response(status_code=204)

# TODO 10: rtechnical debt --> asnych would be very nice, however, i am at the end of my knowledge why this behaves so badly....
@router.post("/configuration/add")
async def add_new_config(configuration: UploadFile = Form(...), name: str = Form(...), description: str = Form(...), file_type: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    file_ending = configuration.filename.split(".")[-1]
    LOGGER.debug(file_ending)
    if not file_type_is_accepted(file_type=file_type, file_ending=file_ending):
        return JSONResponse({"message": f"file in {file_ending} format is not accepted as {file_type} "}, status_code=500)
    # For rulesets and general configurations
    content = await configuration.read()  
    db_configuration = Configuration(
        name=name,
        description=description,
        configuration=content,
        file_type=file_type,
    )
    await add_config(db_configuration)
    return JSONResponse({"message": "configuration added successfully"}, status_code=200)


@router.post("/dataset/add")
async def add_new_dataset(data_file: UploadFile = Form(...),labels_file: UploadFile = Form(...), name: str = Form(...), description: str = Form(...), dataset_type_id: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    data_file_ending = data_file.filename.split(".")[-1]
    labels_file_ending = labels_file.filename.split(".")[-1]
    LOGGER.debug(data_file_ending)
    if not file_type_is_accepted(file_type=FILE_TYPES.TEST_DATA.value ,file_ending=data_file_ending):
        return JSONResponse({"message": f"file in {data_file_ending} format is not accepted as {FILE_TYPES.TEST_DATA.value} "}, status_code=500)
    if not file_type_is_accepted(file_type=FILE_TYPES.TEST_DATA.value ,file_ending=labels_file_ending):
        return JSONResponse({"message": f"file in {labels_file_ending} format is not accepted as {FILE_TYPES.TEST_DATA.value} "}, status_code=500)
    # For rulesets and general configurations
    dataset_type = await get_dataset_type_by_id(int(dataset_type_id))
    data_file = await data_file.read()
    labels_file = await labels_file.read()
    background_tasks.add_task(calculate_and_add_dataset, data_file=data_file, labels_file=labels_file, name=name, description=description, dataset_type=dataset_type)
    return JSONResponse(content={"message": "configuration added successfully"}, status_code=200)


@router.get("/dataset/all")
async def get_all_ds():
    datasets = await get_all_datasets()
    return datasets

@router.delete("/dataset/{id}")
async def remove_dataset( id: int):
    await remove_dataset_by_id(id)
    return Response(status_code=204)


@router.get("/dataset-type/all")
async def get_all_ds_types():
    dataset_types = await get_all_dataset_types()
    return dataset_types


@router.get("/ids-tool/all")
async def get_all_ids_tools():
    return await get_all_tools()

@router.get("/container/all")
async def get_all_ids_container():
    return await get_all_container()

@router.get("/container/without/ensemble")
async def get_all_ids_container_not_assigned_to_an_ensemble():
    container = await get_all_container()
    ensemble_ids = await get_all_ensemble_container()
    id_list = [e.ids_container_id for e in ensemble_ids]
    available_container = [ c for c in container if c.id not in id_list ]
    return available_container


@router.patch("/container")
async def patch_container(container: IdsContainerUpdate,):
    await update_container(container)
    return JSONResponse({"message": "updated container successfully"}, status_code = 200)


@router.get("/ensemble/technique/all")
async def get_ensemble_techniques():
    return await get_all_ensemble_techniques()

@router.get("/ensemble/all")
async def get_ensembles():
    return await get_all_ensembles()

@router.get("/ensemble/container/all")
async def get_ensembles():
    return await get_all_ensemble_container()

@router.patch("/ensemble")
async def patch_ensemble(ensmeble: EnsembleUpdate,):
    result = await update_ensemble(ensmeble)
    for r in result:
        if r.status_code != 200:
            return JSONResponse(content={"error": "Failed to change ensemble attributes"}, status_code=500)
        else:
            return JSONResponse(content={"messages": "successfully changed ensemble attributes"}, status_code=200)
        

@router.get("/host/all")
async def return_all_hosts():
    hosts = await get_all_hosts()
    return hosts

@router.post("/host/add")
async def create_host(host_data: DockerHostCreationData,):
    host = DockerHostSystem(
        name = host_data.name,
        host = host_data.host,
        docker_port = host_data.docker_port
    )
    await add_host_system(host)
    return JSONResponse(content={"message": "Successfully created host"}, status_code=200)

@router.delete("/host/delete/{id}")
async def delete_host(id: int,):
    await remove_host(id)
    return Response(status_code=204)
