import asyncio
from http.client import HTTPResponse
import json
import uuid
from ..utils import ANALYSIS_STATUS,STATUS, read_data_file, create_response_error ,create_response_message, deregister_container_from_ensemble, parse_response_for_triggered_analysis
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session
from .ensemble_ids import EnsembleIds, get_ensemble_ids_by_ids
from ..database import Base, get_db_session_context
from .ids_container import IdsContainer, update_container_status
from ..validation.models import EnsembleUpdate
import httpx 
from sqlalchemy.future import select
from ..logger import LOGGER
class Ensemble(Base):
    __tablename__ = "ensemble"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    technique_id = Column(Integer, ForeignKey("ensemble_technique.id"))
    status = Column(String(32), nullable=False)
    description = Column(String(2048))
    current_analysis_id = Column(String(64))

    ensemble_ids = relationship('EnsembleIds', back_populates='ensemble', cascade="all, delete", lazy="selectin")
    ensemble_technique = relationship('EnsembleTechnique', back_populates='ensemble', lazy="selectin")

    async def add_container(self,container_id: int):
        from .ids_container import IdsContainer, get_container_by_id
        async with get_db_session_context() as db:
            ensemble_ids = EnsembleIds(
                ensemble_id=self.id,
                ids_container_id=container_id,
                status=ANALYSIS_STATUS.IDLE.value
            )
            container: IdsContainer = await get_container_by_id(container_id)
            container_url = container.get_container_http_url()
            endpoint = f"/configure/ensemble/add/{self.id}"
            async with httpx.AsyncClient() as client:
                    response: HTTPResponse = await client.post(container_url+endpoint)
            if response.status_code == 200:
                db.add(ensemble_ids)
                await db.commit()
            return response
    
    async def remove_container(self, container_id: int):
        from .ids_container import IdsContainer, get_container_by_id
        async with get_db_session_context() as db:
            ensemble_ids = await get_ensemble_ids_by_ids(self.id, container_id)

            container: IdsContainer = await get_container_by_id(container_id)
            response = await deregister_container_from_ensemble(container)

            if response.status_code == 200:
                await db.delete(ensemble_ids)
                await db.commit()

            return response

    async def get_ensemble_ids(self):
        async with get_db_session_context() as db:
            stmt = select(EnsembleIds).where(EnsembleIds.ensemble_id == self.id)
            result = await db.execute(stmt)
            return result.scalars().all()

    async def get_assigned_containers(self):
        from .ids_container import IdsContainer
        async with get_db_session_context() as db:
            ensemble_ids = await self.get_ensemble_ids()
            id_list = [e_ids.ids_container_id for e_ids in ensemble_ids]
            stmt = select(IdsContainer).where(IdsContainer.id.in_(id_list))
            container_result = await db.execute(stmt)
            return container_result.scalars().all()
    
    async def start_static_analysis(self, dataset):
        from .ids_container import IdsContainer
        async with get_db_session_context() as db:

            containers: list[IdsContainer] = await self.get_assigned_containers()
            responses = []
            data_file = await read_data_file(dataset)

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
                    LOGGER.debug(f"respoonse for {container.name} was {response.status}")
                    await update_container_status(STATUS.IDLE.value, container)
                else:
                    LOGGER.debug(f"Container {container.name} started sucessfully, now it is active")
                    await update_container_status(STATUS.ACTIVE.value, container)
                responses.append(response)
            return responses
    
    async def container_is_last_one_running(self, container):
        async with get_db_session_context() as db:

            all_containers = await self.get_assigned_containers()
            other_containers_in_ensemble = list(filter(lambda c: c.id != container.id, all_containers))
            other_containers_running = [ await c.is_busy() for c in other_containers_in_ensemble]    
            # if there is only one container in the ensemble, then that is always the last one running
            if len(all_containers) == 1:
                return True
            elif True not in other_containers_running:
                return True
            else:
                return False


    async def start_network_analysis(self, network_analysis_data):
        from .ids_container import IdsContainer
        async with get_db_session_context() as db:

            containers: list[IdsContainer] = await self.get_assigned_containers()
            responses = []

            for container in containers:
                data = json.dumps(network_analysis_data.__dict__)
                response: HTTPResponse = await container.start_network_analysis(data)
                response = await parse_response_for_triggered_analysis(response, container, "network", self.id)
                if response.status_code != 200:
                    LOGGER.debug(f"respoonse for {container.name} was {response.status}")
                    await update_container_status(STATUS.IDLE.value, container)
                else:
                    LOGGER.debug(f"Container {container.name} started sucessfully, now it is active")
                    await update_container_status(STATUS.ACTIVE.value, container)            
                responses.append(response)  
            return responses

    async def stop_analysis(self):
        async with get_db_session_context() as db:

            containers: list[IdsContainer] = await self.get_assigned_containers()

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
        
async def generate_new_analysis_id(ensemble):
    async with get_db_session_context() as db:
        ensemble = await db.merge(ensemble)
        ensemble.current_analysis_id = str(uuid.uuid4())
        await db.commit()
        await db.refresh(ensemble)
        

async def unset_analysis_id(ensemble):
    async with get_db_session_context() as db:
        ensemble = await db.merge(ensemble)
        ensemble.current_analysis_id = None
        await db.commit()
        await db.refresh(ensemble)

async def get_all_ensembles():
    async with get_db_session_context() as db:
        stmt = select(Ensemble)
        result = await db.execute(stmt)
        return result.scalars().all()  # Return all results

async def get_ensemble_by_id(id: int):
    async with get_db_session_context() as db:
        stmt = select(Ensemble).where(Ensemble.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()  # Return a single row or None

async def remove_ensemble(ensemble: Ensemble):
    async with get_db_session_context() as db:
        await db.delete(ensemble)
        await db.commit()  # Commit asynchronously

async def add_ensemble(ensemble: Ensemble):
    async with get_db_session_context() as db:
        db.add(ensemble)
        await db.commit()  # Commit asynchronously
        await db.refresh(ensemble)  # Refresh to get updated values

async def update_ensemble(ensemble: EnsembleUpdate):
    async with get_db_session_context() as db:
        stmt = select(Ensemble).where(Ensemble.id == ensemble.id)
        result = await db.execute(stmt)
        ensemble_db = result.scalar_one_or_none()
        
        if not ensemble_db:
            return None  # Handle case where Ensemble not found

        former_containers = [ensemble_container.ids_container_id for ensemble_container in await ensemble_db.get_ensemble_ids(db)]
        
        # Update ensemble attributes
        for key, value in ensemble.dict().items():
            setattr(ensemble_db, key, value)
        
        await db.commit()
        await db.refresh(ensemble_db)  # Refresh after commit
        
        new_containers = ensemble.container_ids
        added_containers = list(filter(lambda x: x not in former_containers, new_containers))
        removed_containers = list(filter(lambda x: x not in new_containers, former_containers))

        responses = []

        for container_id in removed_containers:
            res = await ensemble_db.remove_container(container_id)
            responses.append(res)

        for container_id in added_containers:
            res = await ensemble_db.add_container(container_id)
            responses.append(res)
        
        return responses

async def update_ensemble_status(status: STATUS, ensemble: Ensemble):
    async with get_db_session_context() as db:
        ensemble = await db.merge(ensemble)
        ensemble.status = status
        await db.commit()  # Commit asynchronously
        await db.refresh(ensemble)  # Refresh after commit