import base64
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from ..database import get_db
from ..models.configuration import get_all_configurations, remove_configuration_by_id, add_config,Configuration, get_all_configurations_by_type
from ..models.dataset import Dataset, get_all_datasets, remove_dataset_by_id
from ..models.ids_tool import get_all_tools
from ..models.ids_container import get_all_container, update_container
from ..models.ensemble import get_all_ensembles, update_ensemble
from ..models.ensemble_technique import get_all_ensemble_techniques
from ..models.ensemble_ids import get_all_ensemble_container
from ..utils import FILE_TYPES, get_serialized_confgigurations, calculate_and_add_dataset, get_serialized_datasets
from ..validation.models import EnsembleUpdate, IdsContainerUpdate, DockerHostCreationData
from ..models.docker_host_system import get_all_hosts, remove_host, add_host_system, DockerHostSystem
router = APIRouter(
    prefix="/crud"
)



@router.get("/configuration/all")
async def get_all_configs(db=Depends(get_db)):
    configurations = get_all_configurations(db)
    serialized_configurations = get_serialized_confgigurations(configurations)
    return serialized_configurations

@router.get("/configuration/file-types")
async def get_all_config_filetypes(db=Depends(get_db)):
    types = [t.value for t in FILE_TYPES]
    return types


@router.get("/configuration/all/{file_type}")
async def get_all_configs_of_a_filetype(file_type: str, db=Depends(get_db)):
    valid_file_types = [t.value for t in FILE_TYPES]
    if file_type in valid_file_types:
        configurations = get_all_configurations_by_type(db, file_type)
        serialized_configurations = get_serialized_confgigurations(configurations)
        return serialized_configurations
    else:
        return {"message": "wrong file type"}

@router.delete("/configuration/{id}")
async def remove_config( id: int, db=Depends(get_db)):
    remove_configuration_by_id(db, id)
    return Response(status_code=204)

# TODO 10: rtechnical debt --> asnych would be very nice, however, i am at the end of my knowledge why this behaves so badly....
@router.post("/configuration/add")
async def add_new_config(configuration: list[UploadFile] = Form(...), name: str = Form(...), description: str = Form(...), file_type: str = Form(...), db=Depends(get_db), background_tasks: BackgroundTasks = BackgroundTasks()):
    # For rulesets and general configurations
    content = await configuration[0].read()  
    configuration = Configuration(
        name=name,
        description=description,
        configuration=content,
        file_type=file_type,
    )
    add_config(db, configuration)
    return JSONResponse({"message": "configuration added successfully"}, status_code=200)


@router.post("/dataset/add")
async def add_new_dataset(configuration: list[UploadFile] = Form(...), name: str = Form(...), description: str = Form(...), db=Depends(get_db), background_tasks: BackgroundTasks = BackgroundTasks()):
    # For rulesets and general configurations
    if len(configuration) == 2:
        pcap_file = await list(filter(lambda c: c.filename.split(".")[-1] == "pcap" , configuration ))[0].read()
        labels_file = await list(filter(lambda c: c.filename.split(".")[-1] != "pcap" , configuration ))[0].read()
        background_tasks.add_task(calculate_and_add_dataset, pcap_file=pcap_file, labels_file=labels_file, name=name, description=description, db=db)
        return JSONResponse(content={"message": "configuration added successfully"}, status_code=200)
    else:
        return JSONResponse(content={"message": "Too many files attached"}, status_code=500)


@router.get("/dataset/all")
async def get_all_ds(db=Depends(get_db)):
    datasets = get_all_datasets(db)
    serialized_datasets = get_serialized_datasets(datasets)
    return serialized_datasets

@router.delete("/dataset/{id}")
async def remove_dataset( id: int, db=Depends(get_db)):
    remove_dataset_by_id(db, id)
    return JSONResponse(content={"message": f"Successfully removed dataset with id {id}"}, status_code=204)

@router.get("/ids-tool/all")
async def get_all_ids_tools(db=Depends(get_db)):
    return get_all_tools(db)

@router.get("/container/all")
async def get_all_ids_container(db=Depends(get_db)):
    return get_all_container(db)

# TODO add test methods for these as well
@router.get("/container/without/ensemble")
async def get_all_available_ids_container(db=Depends(get_db)):
    container = get_all_container(db)
    ensemble_ids = get_all_ensemble_container(db)
    id_list = [e.ids_container_id for e in ensemble_ids]
    available_container = [ c for c in container if c.id not in id_list ]
    print(available_container)
    return available_container


@router.patch("/container")
async def patch_container(container: IdsContainerUpdate,db=Depends(get_db)):
    await update_container(container, db)
    return {"message": "updated container successfully"}


@router.get("/ensemble/technique/all")
async def get_ensemble_techniques(db=Depends(get_db)):
    return get_all_ensemble_techniques(db)

@router.get("/ensemble/all")
async def get_ensembles(db=Depends(get_db)):
    return get_all_ensembles(db)

@router.get("/ensemble/container/all")
async def get_ensembles(db=Depends(get_db)):
    return get_all_ensemble_container(db)

@router.patch("/ensemble")
async def patch_ensemble(ensmeble: EnsembleUpdate,db=Depends(get_db)):
    result = await update_ensemble(ensmeble, db)
    for r in result:
        if r.status_code != 200:
            return JSONResponse(content={"messages": "Failed to change ensemble attributes"}, status_code=500)
        else:
            return JSONResponse(content={"messages": "successfully changed ensemble attributes"}, status_code=200)
        

@router.get("/host/all")
async def return_all_hosts(db=Depends(get_db)):
    hosts = get_all_hosts(db)
    return hosts

@router.post("/host/add")
async def create_host(host_data: DockerHostCreationData,db=Depends(get_db)):
    host = DockerHostSystem(
        name = host_data.name,
        host = host_data.host,
        docker_port = host_data.docker_port
    )
    add_host_system(host, db)
    return JSONResponse(content={"message": "Successfully created host"}, status_code=200)

@router.delete("/host/delete/{id}")
async def delete_host(id: int,db=Depends(get_db)):
    remove_host(id, db)
    return Response(status_code=204)
