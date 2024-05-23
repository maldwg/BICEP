from fastapi import APIRouter, Depends
from ..dependencies import get_db
from ..validation.models import EnsembleCreate
from ..models.ensemble import get_all_ids_ensembles, Ensemble, add_ensemble, get_ensemble_by_id, remove_ensemble

from ..utils import find_free_port, STATUS

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