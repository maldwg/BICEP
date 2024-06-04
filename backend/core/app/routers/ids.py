from fastapi import APIRouter, Depends
from ..dependencies import get_db
from ..validation.models import IdsContainerCreate, EnsembleCreate
from ..models.ids_container import IdsContainer, get_container_by_id
from ..models.configuration import Configuration
from ..utils import find_free_port, STATUS

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
