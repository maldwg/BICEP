from fastapi import APIRouter, Depends
from ..dependencies import get_db
from ..validation.models import IdsContainerCreate
from ..models.ids_container import IdsContainer, get_container_by_id
from ..models.configuration import Configuration
from ..utils import find_free_port, STATUS

router = APIRouter(
    prefix="/ids"
)


@router.post("/setup")
async def setup_ids(data: IdsContainerCreate, db=Depends(get_db)):
    free_port=find_free_port()
    ids_container = IdsContainer(
        host=data.host,
        port=free_port,
        description=data.description,
        configuration_id=data.configurationId,
        ids_tool_id=data.idsToolId,
        status=STATUS.ACTIVE
        )
    await ids_container.setup(db)
    return {"message": "setup done"}

@router.delete("/remove/{container_id}")
async def remove_container(container_id: int, db=Depends(get_db)):
    container = get_container_by_id(db, container_id)
    await container.teardown(db)
    return {"message": "teardown done"}









@router.get("/testfile")
async def inject_test(db = Depends(get_db)):
    file="/tmp/test-config.yaml"
    with open('/tmp/test-config.yaml', 'rb') as file:
        binary_data = file.read()
    c = Configuration(name="testfile" ,description="test", configuration=binary_data)
    db.add(c)
    db.commit()
