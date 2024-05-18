from fastapi import APIRouter, Depends
import crud
from ..dependencies import get_db
from ..validation.models import IdsContainerCreate
from ..models.ids_container import IdsContainer

router = APIRouter(
    prefix="/ids"
)


@router.post("/setup")
async def setup_ids(data: IdsContainerCreate, db=Depends(get_db)):
    ids_tool = crud.get_ids_by_id(db, data.ids_tool_id)
    config = crud.get_config_by_id(db, data.configuration_id)
    return await setup_ids_container()

async def setup_ids_container():
    pass
    # get url
    # get new port 
    # execute setup command
    # return what exactly?
    ids_container = IdsContainer()