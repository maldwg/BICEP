from fastapi import APIRouter, Depends, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from app.models.configuration import get_config_by_id, get_all_configurations, get_serialized_configuration, remove_configuration_by_id, add_config,Configuration, get_all_configurations_by_type, update_configuration
from app.models.dataset import get_all_datasets, remove_dataset_by_id
from app.models.ids_tool import IdsTool, get_all_tools, add_ids_tool, update_ids_tool, delete_ids_tool
from app.models.ids_system import get_all_container, update_container
from app.models.ensemble import get_all_ensembles, update_ensemble
from app.models.ensemble_technique import get_all_ensemble_techniques
from app.models.ensemble_ids import get_all_ensemble_container
from app.models.benchmarking import get_all_benchmarking_results
from app.utils import DOCKER_HOST_STATUS, FILE_TYPES, calculate_and_add_dataset, file_type_is_accepted, create_directory, remove_directory
from app.validation.models import EnsembleUpdate, IdsContainerUpdate, DockerHostCreationData, IdsToolCreate, IdsToolUpdate, ConfigurationUpdate
from app.models.docker_host_system import get_all_hosts, remove_host, add_host_system, DockerHostSystem
from app.models.dataset_types import get_dataset_type_by_id, get_all_dataset_types
from app.models.metric_service import serialize_metric_service
from app.logger import LOGGER
from app.database import get_db
import uuid
import shutil
import os
import yaml

router = APIRouter(
    prefix="/crud"
)


def serialize_host(host: DockerHostSystem) -> dict:
    metric_service = serialize_metric_service(getattr(host, "metric_service", None))

    status_message = None
    if host.status == DOCKER_HOST_STATUS.UNAVAILABLE.value:
        if metric_service and metric_service.get("status") != DOCKER_HOST_STATUS.AVAILABLE.value:
            status_message = metric_service.get("status_message")
        else:
            status_message = "Docker host is unavailable."

    return {
        "id": host.id,
        "name": host.name,
        "host": host.host,
        "docker_port": host.docker_port,
        "status": host.status,
        "status_message": status_message,
        "metric_service": metric_service,
    }

@router.get("/benchmarking-results/all")
async def get_benchmarking_results(db=Depends(get_db)):
    benchmarking_results = await get_all_benchmarking_results(db)
    return benchmarking_results

@router.get("/configuration/all")
async def get_all_configs(db=Depends(get_db)):
    configurations = await get_all_configurations(db)
    return configurations

@router.get("/configuration/file-types")
async def get_all_config_filetypes():
    types = [t.value for t in FILE_TYPES]
    return types


@router.get("/configuration/all/{file_type}")
async def get_all_configs_of_a_filetype(file_type: str, db=Depends(get_db)):
    valid_file_types = [t.value for t in FILE_TYPES]
    if file_type in valid_file_types:
        configurations = await get_all_configurations_by_type(db, file_type)
        return configurations
    else:
        return {"error": "wrong file type"}

@router.delete("/configuration/{id}")
async def remove_config( id: int, db=Depends(get_db)):
    configuration = await get_config_by_id(db, id)
    configuration_directoy = "/".join(configuration.file_path.split("/")[:-1])
    await remove_directory(configuration_directoy)
    await remove_configuration_by_id(db, id)
    return Response(status_code=204)


@router.get("/configuration/{id}/serialized")
async def get_config_content( id: int, db=Depends(get_db)):
    configuration = await get_config_by_id(db, id)
    if configuration is None:
        return JSONResponse({"error": "Configuration not found"}, status_code=404)
    return await get_serialized_configuration(configuration)


@router.patch("/configuration")
async def patch_configuration(configuration_data: ConfigurationUpdate, db=Depends(get_db)):
    configuration = await update_configuration(db, configuration_data)
    if configuration is None:
        return JSONResponse({"error": "Configuration not found"}, status_code=404)
    return await get_serialized_configuration(configuration)

@router.get("/configuration/{id}/services")
async def get_config_services(id: int, db=Depends(get_db)):
    try:
        configuration = await get_config_by_id(db, id)
        content = await configuration.read_content()
        # Parse YAML
        compose_data = yaml.safe_load(content)
        if not compose_data or 'services' not in compose_data:
            return []
            
        services = []
        for name, params in compose_data['services'].items():
            labels = params.get("labels", {})
            is_sensor = False
            config_mount_path = None
            if isinstance(labels, dict):
                is_sensor = labels.get("bicep.sensor") in ("true", True, "1")
                config_mount_path = labels.get("bicep.config.mount")
            elif isinstance(labels, list):
                for label in labels:
                    if not isinstance(label, str):
                        continue
                    if label.startswith("bicep.sensor="):
                        is_sensor = label.split("=", 1)[1].lower() in ("true", "1")
                    elif label.startswith("bicep.config.mount="):
                        config_mount_path = label.split("=", 1)[1]

            expected_config_extension = None
            if config_mount_path:
                expected_config_extension = (
                    os.path.splitext(config_mount_path)[1].lower() or None
                )
            
            services.append({
                "name": name,
                "is_sensor": is_sensor,
                "config_mount_path": config_mount_path,
                "expected_config_extension": expected_config_extension,
            })
            
        return services
    except Exception as e:
        LOGGER.error(f"Error parsing services for config {id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/configuration/add")
async def add_new_config(configuration: UploadFile = Form(...), name: str = Form(...), description: str = Form(...), file_type: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks(), db=Depends(get_db)):
    file_name = configuration.filename
    if not file_type_is_accepted(file_type=file_type, file_ending=file_name.split(".")[-1]):
        return JSONResponse({"error": f"file in {file_name.split('.')[-1]} format is not accepted as {file_type}"}, status_code=500)
    if file_type == FILE_TYPES.RUNTIME.value:
        base_path = os.getenv("RUNTIME_STORE_BASE_PATH")
    elif file_type == FILE_TYPES.DEPLOYMENT.value:
        base_path = os.getenv("DEPLOYMENT_STORE_BASE_PATH")
    elif file_type == FILE_TYPES.RULESET.value:
        base_path = os.getenv("RULESET_STORE_BASE_PATH")
    else:
        return JSONResponse({"error": f"filetype {file_type} not found "}, status_code=500)
    uid = str(uuid.uuid4())
    configuration_storage_location = f"{base_path}/{uid}" 
    configuration_file_path = f"{configuration_storage_location}/{file_name}"
    await create_directory(configuration_storage_location)
    with open(configuration_file_path, "wb") as f_out:
        shutil.copyfileobj(configuration.file, f_out)
        
    db_configuration = Configuration(
        name=name,
        description=description,
        file_path=configuration_file_path,
        file_type=file_type,
    )
    
    await add_config(db, db_configuration)
    return JSONResponse({"message": "configuration added successfully"}, status_code=200)


@router.post("/dataset/add")
async def add_new_dataset(data_file: UploadFile = Form(...),labels_file: UploadFile = Form(...), name: str = Form(...), description: str = Form(...), dataset_type_id: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks(), db=Depends(get_db)):
    data_file_ending = data_file.filename.split(".")[-1]
    labels_file_ending = labels_file.filename.split(".")[-1]
    if not file_type_is_accepted(file_type=FILE_TYPES.DATASET.value ,file_ending=data_file_ending):
        return JSONResponse({"error": f"file in {data_file_ending} format is not accepted as {FILE_TYPES.DATASET.value} "}, status_code=500)
    if not file_type_is_accepted(file_type=FILE_TYPES.DATASET.value ,file_ending=labels_file_ending):
        return JSONResponse({"error": f"file in {labels_file_ending} format is not accepted as {FILE_TYPES.DATASET.value} "}, status_code=500)
    # For rulesets and general configurations
    dataset_type = await get_dataset_type_by_id(db, int(dataset_type_id))
    
    uid = str(uuid.uuid4())
    base_path = os.getenv("DATASET_BASE_PATH")
    dataset_storage_location = f"{base_path}/{name}/{uid}" 
    data_file_path = f"{dataset_storage_location}/dataset.{data_file_ending}"
    labels_file_path = f"{dataset_storage_location}/dataset.{labels_file_ending}"    
    await create_directory(dataset_storage_location)
    # Move the files to not write them again to file

    with open(data_file_path, "wb") as f_out:
        shutil.copyfileobj(data_file.file, f_out)

    with open(labels_file_path, "wb") as f_out:
        shutil.copyfileobj(labels_file.file, f_out)
    
    background_tasks.add_task(calculate_and_add_dataset, data_file_path=data_file_path, labels_file_path=labels_file_path, name=name, description=description, dataset_type=dataset_type, db=db)
    return JSONResponse(content={"message": "configuration added successfully"}, status_code=200)


@router.get("/dataset/all")
async def get_all_ds(db=Depends(get_db)):
    datasets = await get_all_datasets(db)
    return datasets

@router.delete("/dataset/{id}")
async def remove_dataset( id: int, db=Depends(get_db)):
    await remove_dataset_by_id(db, id)
    return Response(status_code=204)


@router.get("/dataset-type/all")
async def get_all_ds_types(db=Depends(get_db)):
    dataset_types = await get_all_dataset_types(db)
    return dataset_types


@router.get("/ids-tool/all")
async def get_all_ids_tools(db=Depends(get_db)):
    return await get_all_tools(db)

@router.get("/container/all")
async def get_all_ids_container(include_deleted: bool = False, db=Depends(get_db)):
    return await get_all_container(db, include_deleted=include_deleted)

@router.get("/container/without/ensemble")
async def get_all_ids_container_not_assigned_to_an_ensemble(db=Depends(get_db)):
    container = await get_all_container(db, include_deleted=False)
    ensemble_ids = await get_all_ensemble_container(db)
    id_list = [e.ids_system_id for e in ensemble_ids]
    available_container = [ c for c in container if c.id not in id_list ]
    return available_container


@router.patch("/container")
async def patch_container(container: IdsContainerUpdate,db=Depends(get_db)):
    await update_container(db, container)
    return JSONResponse({"message": "updated container successfully"}, status_code = 200)


@router.get("/ensemble/technique/all")
async def get_ensemble_techniques(db=Depends(get_db)):
    return await get_all_ensemble_techniques(db)

@router.get("/ensemble/all")
async def get_ensembles(db=Depends(get_db)):
    return await get_all_ensembles(db)

@router.get("/ensemble/container/all")
async def get_ensembles(db=Depends(get_db)):
    return await get_all_ensemble_container(db)

@router.patch("/ensemble")
async def patch_ensemble(ensmeble: EnsembleUpdate, db=Depends(get_db)):
    result = await update_ensemble(db, ensmeble)
    for r in result:
        if r.status_code != 200:
            return JSONResponse(content={"error": "Failed to change ensemble attributes"}, status_code=500)
        else:
            return JSONResponse(content={"messages": "successfully changed ensemble attributes"}, status_code=200)
        
@router.get("/host/all")
async def return_all_hosts(db=Depends(get_db)):
    hosts = await get_all_hosts(db)
    return [serialize_host(host) for host in hosts]

@router.post("/host/add")
async def create_host(host_data: DockerHostCreationData, db=Depends(get_db)):
    host = DockerHostSystem(
        name = host_data.name,
        host = host_data.host,
        docker_port = host_data.docker_port,
        status = DOCKER_HOST_STATUS.UNAVAILABLE.value
    )
    await add_host_system(db, host)
    return JSONResponse(content={"message": "Successfully created host"}, status_code=200)


@router.delete("/host/delete/{id}")
async def delete_host(id: int,db=Depends(get_db)):
    try:
        removed = await remove_host(db, id)
    except RuntimeError as exc:
        LOGGER.error(f"Failed to delete docker host {id}: {exc}")
        return JSONResponse(content={"error": str(exc)}, status_code=500)

    if not removed:
        return JSONResponse(
            content={"error": f"Docker host with id {id} was not found"},
            status_code=404,
        )

    return Response(status_code=204)


@router.post("/ids-tool/add")
async def create_ids_tool(tool_data: IdsToolCreate, db=Depends(get_db)):
    tool = IdsTool(
        name=tool_data.name,
        ids_type=tool_data.ids_type,
        analysis_method=tool_data.analysis_method,
        requires_ruleset=tool_data.requires_ruleset,
        image_name=tool_data.image_name,
        image_tag=tool_data.image_tag,
        deployment_type=tool_data.deployment_type,
    )
    await add_ids_tool(db, tool)
    return JSONResponse(content={"message": "Successfully created IDS Tool"}, status_code=200)


@router.patch("/ids-tool")
async def patch_ids_tool(tool_data: IdsToolUpdate, db=Depends(get_db)):
    result = await update_ids_tool(db, tool_data)
    if result is None:
        return JSONResponse(content={"error": "IDS Tool not found"}, status_code=404)
    return JSONResponse(content={"message": "Successfully updated IDS Tool"}, status_code=200)


@router.delete("/ids-tool/delete/{id}")
async def remove_ids_tool(id: int, db=Depends(get_db)):
    result = await delete_ids_tool(db, id)
    if result is None:
        return JSONResponse(content={"error": "IDS Tool not found"}, status_code=404)
    return Response(status_code=204)
