from http.client import HTTPResponse
import json
import uuid
from app.utils import ANALYSIS_STATUS,STATUS, read_data_file, create_response_error ,create_response_message, deregister_container_from_ensemble, parse_response_for_triggered_analysis
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session, selectinload
from app.models.ensemble_ids import EnsembleIds, get_ensemble_ids_by_ids
from app.database import Base
from app.models.ids_container import IdsContainer, update_container_status
from app.validation.models import EnsembleUpdate
import httpx 
from sqlalchemy.future import select
from app.logger import LOGGER
from sqlalchemy.ext.asyncio import AsyncSession

class Ensemble(Base):
    __tablename__ = "ensemble"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    technique_id = Column(Integer, ForeignKey("ensemble_technique.id"))
    status = Column(String(32), nullable=False)
    description = Column(String(2048))
    current_analysis_id = Column(String(64))

    ensemble_ids = relationship('EnsembleIds', cascade="all, delete", lazy="selectin")
    ensemble_technique = relationship('EnsembleTechnique', back_populates='ensemble', lazy="selectin")

    async def add_container(self, db: AsyncSession, container_id: int):
        from app.models.ids_container import IdsContainer, get_container_by_id
        ensemble_ids = EnsembleIds(
            ensemble_id=self.id,
            ids_container_id=container_id,
            status=ANALYSIS_STATUS.IDLE.value
        )
        container: IdsContainer = await get_container_by_id(db, container_id)
        container_url = container.get_container_http_url()
        endpoint = f"/configure/ensemble/add/{self.id}"
        async with httpx.AsyncClient() as client:
                response: HTTPResponse = await client.post(container_url+endpoint)
        if response.status_code == 200:
            db.add(ensemble_ids)
            await db.commit()
        return response
    
    async def remove_container(self, db: AsyncSession, container_id: int):
        from app.models.ids_container import IdsContainer, get_container_by_id
        ensemble_ids = await get_ensemble_ids_by_ids(db, self.id, container_id)
        container: IdsContainer = await get_container_by_id(db, container_id)
        response = await deregister_container_from_ensemble(container)
        if response.status_code == 200:
            await db.delete(ensemble_ids)
            await db.commit()
        return response

    async def get_ensemble_ids(self, db: AsyncSession):
        stmt = select(EnsembleIds).where(EnsembleIds.ensemble_id == self.id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_assigned_containers(self, db: AsyncSession):
        # refactor to not rely on the relationship shit
        from app.models.ids_container import IdsContainer
        ensemble_ids = await self.get_ensemble_ids(db)
        id_list = [e_ids.ids_container_id for e_ids in ensemble_ids]
        stmt = select(IdsContainer).where(IdsContainer.id.in_(id_list))
        container_result = await db.execute(stmt)
        return container_result.scalars().all()



    async def start_static_analysis(self, db: AsyncSession, dataset_id: int):
        from app.models.ids_container import IdsContainer          
        from app.models.dataset import get_dataset_by_id 
        LOGGER.debug(f"{dataset_id}")
        dataset = await get_dataset_by_id(db, dataset_id)
        containers: list[IdsContainer] = await self.get_assigned_containers(db)
        responses = []
        data_file = await read_data_file(dataset.data_file_path)
        for container in containers:
            form_data= {
                "container_id": (None, str(container.id), "application/json"),
                "ensemble_id": (None, str(self.id), "application/json"),
                "dataset": (dataset.name, data_file, "application/octet-stream"),
                "dataset_id": (None, str(dataset.id), "application/json")
            }    
            
            # TODO 0: try with asyncio in background 
            response: HTTPResponse = await container.start_static_analysis(form_data, dataset)
            response = await parse_response_for_triggered_analysis(response, container, "static", self.id)
            if response.status_code != 200:
                await update_container_status(db, STATUS.IDLE.value, container)
            else:
                await update_container_status(db, STATUS.ACTIVE.value, container)
            responses.append(response)
        return responses
    
    async def container_is_last_one_running(self, db: AsyncSession, container):
        all_containers = await self.get_assigned_containers(db)
        other_containers_in_ensemble = list(filter(lambda c: c.id != container.id, all_containers))
        other_containers_running = [ await c.is_busy() for c in other_containers_in_ensemble]    
        # if there is only one container in the ensemble, then that is always the last one running
        if len(all_containers) == 1:
            return True
        elif True not in other_containers_running:
            return True
        else:
            return False


    async def start_network_analysis(self, db: AsyncSession, network_analysis_data):
        from app.models.ids_container import IdsContainer
        containers: list[IdsContainer] = await self.get_assigned_containers(db)
        responses = []
        for container in containers:
            data = json.dumps(network_analysis_data.__dict__)
            response: HTTPResponse = await container.start_network_analysis(data)
            response = await parse_response_for_triggered_analysis(response, container, "network", self.id)
            if response.status_code != 200:
                await update_container_status(db, STATUS.IDLE.value, container)
            else:
                await update_container_status(db, STATUS.ACTIVE.value, container)            
            responses.append(response)  
        return responses

    async def stop_analysis(self, db:AsyncSession):
        containers: list[IdsContainer] = await self.get_assigned_containers(db)
        responses = []
        for container in containers:
            response: HTTPResponse = await container.stop_analysis()
            if response.status_code == 200:
                message= f"Analysis for container {container.id} successfully stopped"
                responses.append(create_response_message(message, 200))
            else:
                message=f"Analysis for container {container.id} could not be stopped"
                responses.append(create_response_error(message, 500)) 
        return responses
    
    async def is_container_running(self):
        if self.status == STATUS.ACTIVE:
            return True
        else:
            return False
        
    async def generate_new_analysis_id(self, db: AsyncSession):
        self.current_analysis_id = str(uuid.uuid4())
        await db.commit()
        await db.refresh(self)
            

    async def unset_analysis_id(self, db: AsyncSession):
        self.current_analysis_id = None
        await db.commit()
        await db.refresh(self)

async def get_all_ensembles(db: AsyncSession):
    stmt = select(Ensemble).options(
        selectinload(Ensemble.ensemble_ids),
        )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_ensemble_by_id(db: AsyncSession, id: int):
    stmt = select(Ensemble).options(
        selectinload(Ensemble.ensemble_ids),
        ).where(Ensemble.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def remove_ensemble(db: AsyncSession, ensemble: Ensemble):
    await db.delete(ensemble)
    await db.commit()

async def add_ensemble(db: AsyncSession, ensemble: Ensemble):
    db.add(ensemble)
    await db.commit()
    await db.refresh(ensemble)

async def update_ensemble(db: AsyncSession, ensemble: EnsembleUpdate):
    stmt = select(Ensemble).where(Ensemble.id == ensemble.id)
    result = await db.execute(stmt)
    ensemble_db = result.scalar_one_or_none()
    
    if not ensemble_db:
        return None 
    former_containers = [ensemble_container.ids_container_id for ensemble_container in await ensemble_db.get_ensemble_ids(db)]
    
    # Update ensemble attributes
    for key, value in ensemble.model_dump().items():
        setattr(ensemble_db, key, value)
    
    await db.commit()
    await db.refresh(ensemble_db)
    
    new_containers = ensemble.container_ids
    added_containers = list(filter(lambda x: x not in former_containers, new_containers))
    removed_containers = list(filter(lambda x: x not in new_containers, former_containers))
    responses = []
    for container_id in removed_containers:
        res = await ensemble_db.remove_container(db, container_id)
        responses.append(res)
    for container_id in added_containers:
        res = await ensemble_db.add_container(db, container_id)
        responses.append(res)
    
    return responses

async def update_ensemble_status(db: AsyncSession, status: STATUS, ensemble: Ensemble):
    ensemble.status = status
    await db.commit()
    await db.refresh(ensemble)