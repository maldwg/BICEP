from fastapi import APIRouter, Depends
from ..dependencies import get_db
from ..models.configuration import get_all_configurations
from ..models.ids_tool import get_all_tools
router = APIRouter(
    prefix="/crud"
)



@router.get("/configuration/all")
async def get_all_configs(db=Depends(get_db)):
    return get_all_configurations(db)



@router.get("/ids-tool/all")
async def get_all_ids_tools(db=Depends(get_db)):
    return get_all_tools(db)