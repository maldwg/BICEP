from fastapi import APIRouter, Depends, UploadFile, Form
from ..dependencies import get_db
from ..models.configuration import get_all_configurations, remove_configuration_by_id, add_config,Configuration
from ..models.ids_tool import get_all_tools
from ..models.ids_container import get_all_container, remove_container_by_id, get_container_by_id
from ..docker import remove_docker_container
from ..models.ensemble import get_all_ids_ensembles
from ..models.ensemble_technique import get_all_ensemble_techniques

router = APIRouter(
    prefix="/crud"
)



@router.get("/configuration/all")
async def get_all_configs(db=Depends(get_db)):
    return get_all_configurations(db)

@router.delete("/configuration/{id}")
async def remove_config( id: int, db=Depends(get_db)):
    remove_configuration_by_id(db, id)

@router.post("/configuration/add")
async def add_new_config(configuration: UploadFile = Form(...), name: str = Form(...), description: str = Form(...),  db=Depends(get_db)):
    content = await configuration.read()
    configuration = Configuration(
        name=name,
        description=description,
        configuration=content
    )
    add_config(db, configuration)
    return {"message": "configuration added successfully"}


@router.get("/ids-tool/all")
async def get_all_ids_tools(db=Depends(get_db)):
    return get_all_tools(db)

@router.get("/container/all")
async def get_all_ids_container(db=Depends(get_db)):
    return get_all_container(db)


@router.get("/ensemble/technique/all")
async def get_ensemble_techniques(db=Depends(get_db)):
    return get_all_ensemble_techniques(db)

@router.get("/ensemble/all")
async def get_ensembles(db=Depends(get_db)):
    return get_all_ids_ensembles(db)