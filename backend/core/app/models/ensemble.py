import asyncio
from http.client import HTTPResponse
import json
import uuid
from ..utils import STATUS, create_response_error, stream_metric_tasks ,create_response_message, deregister_container_from_ensemble, get_container_host, parse_response_for_triggered_analysis
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Session
from .ensemble_ids import EnsembleIds, get_ensemble_ids_by_ids
from ..database import Base
from .ids_container import IdsContainer, update_container_status
from ..validation.models import EnsembleUpdate
import httpx 
from ..docker import start_metric_stream, stop_metric_stream

class Ensemble(Base):
    __tablename__ = "ensemble"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    technique_id = Column(Integer, ForeignKey("ensemble_technique.id"))
    status = Column(String(32), nullable=False)
    description = Column(String(2048))

    ensemble_ids = relationship('EnsembleIds', back_populates='ensemble', cascade="all, delete")
    ensemble_technique = relationship('EnsembleTechnique', back_populates='ensemble')


    async def add_container(self,container_id: int, db: Session):
        from .ids_container import IdsContainer
        ensemble_ids = EnsembleIds(
            ensemble_id=self.id,
            ids_container_id=container_id
        )
        container: IdsContainer = db.query(IdsContainer).filter(IdsContainer.id == container_id).first() 
        host = get_container_host(container)
        container_url = f"http://{host}:{container.port}"
        endpoint = f"/configure/ensemble/add/{self.id}"
        async with httpx.AsyncClient() as client:
                response: HTTPResponse = await client.post(container_url+endpoint)
        if response.status_code == 200:
            db.add(ensemble_ids)
            db.commit()
        return response
    
    async def remove_container(self, container_id: int, db: Session):
        from .ids_container import IdsContainer

        ensemble_ids = get_ensemble_ids_by_ids(self.id, container_id, db)

        container: IdsContainer = db.query(IdsContainer).filter(IdsContainer.id == container_id).first() 
        response = deregister_container_from_ensemble(container)

        if response.status_code == 200:
            db.delete(ensemble_ids)
            db.commit()

        return response

    def get_enssemble_ids(self, db: Session):
        return db.query(EnsembleIds).filter(EnsembleIds.ensemble_id == self.id).all()

    def get_containers(self, db: Session):
        from .ids_container import IdsContainer
        ensemble_ids = db.query(EnsembleIds).filter(EnsembleIds.ensemble_id == self.id).all()
        id_list = [e_ids.ids_container_id for e_ids in ensemble_ids]
        containers: list[IdsContainer] = db.query(IdsContainer).filter(IdsContainer.id.in_(id_list)).all()
        return containers
    
    async def start_static_analysis(self, static_analysis_data, dataset, db):
        from .ids_container import IdsContainer
        containers: list[IdsContainer] = self.get_containers(db)
        responses = []

        for container in containers:
            form_data= {
                "container_id": (None, str(container.id), "application/json"),
                "ensemble_id": (None, str(self.id), "application/json"),
                "dataset": (dataset.name, dataset.pcap_file, "application/octet-stream"),
                "dataset_id": (None, str(dataset.id), "application/json")
            }    
            response: HTTPResponse = await container.start_static_analysis(form_data)
            response = await parse_response_for_triggered_analysis(response, container, db, "static", self.id)
            
            if response.status_code == 200:
                # TODO: did not work set container status to active/idle afterwards before
                await update_container_status(STATUS.ACTIVE.value, container, db)
            
            responses.append(response)
        return responses
    
# TODO 10: what about ensembling method implementations ?

    async def start_network_analysis(self, network_analysis_data, db):
        from .ids_container import IdsContainer
        containers: list[IdsContainer] = self.get_containers(db)
        responses = []
    
        for container in containers:
            data = json.dumps(network_analysis_data.__dict__)
            response: HTTPResponse = await container.start_network_analysis(data)
            response = await parse_response_for_triggered_analysis(response, container, db, "network", self.id)
            if response.status_code == 200:
                await update_container_status(STATUS.ACTIVE.value, container, db)
                
            responses.append(response)  
        return responses

    async def stop_analysis(self, db):
        containers: list[IdsContainer] = self.get_containers(db)

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
    

    async def start_metric_collection(self,db):
        containers: list[IdsContainer] = self.get_containers(db)
        for container in containers:
            task_id = str(uuid.uuid4())
            task = asyncio.create_task(start_metric_stream(container, self.name))
            stream_metric_tasks[task_id] = task
            container.stream_metric_task_id = task_id           
            db.commit()
            db.refresh(container)
        return f"successfully started metric collection for ensemble {self.id}"
    
    async def stop_metric_collection(self, db):
        containers: list[IdsContainer] = self.get_containers(db)
        for container in containers:
            if not container.stream_metric_task_id:
                # skip the container if there is no streaming task happening for it, e.g. an analysis hasn't been started
                continue
            await stop_metric_stream(container.stream_metric_task_id)
            del stream_metric_tasks[container.stream_metric_task_id]
            container.stream_metric_task_id = None
            db.commit()
            db.refresh(container)
        return f"successfully stopped metric collection for ensemble {self.id}"
def get_all_ensembles(db: Session):
    return db.query(Ensemble).all()

# TODO: make all db actions asynchronous


def get_ensemble_by_id(id: int, db: Session):
    return db.query(Ensemble).filter(Ensemble.id == id).first()

def remove_ensemble(ensemble: Ensemble, db: Session):
    db.delete(ensemble)
    db.commit()

async def add_ensemble(ensemble: Ensemble, db):
    db.add(ensemble)
    db.commit()


async def update_ensemble(ensemble: EnsembleUpdate, db: Session):
    ensemble_db: Ensemble = db.query(Ensemble).filter(Ensemble.id == ensemble.id).first()
    former_containers = [ensemble_container.ids_container_id for ensemble_container in ensemble_db.get_enssemble_ids(db) ]
    for key, value in ensemble.dict().items():
        setattr(ensemble_db, key, value)
    db.commit()
    db.refresh(ensemble_db)
    new_containers = ensemble.container_ids

    added_containers = list(filter(lambda x: x not in former_containers, new_containers))
    removed_containers = list(filter(lambda x: x not in new_containers, former_containers))

    responses = []

    for container_id in removed_containers:
        res = await ensemble_db.remove_container(container_id, db)
        responses.append(res)
    for container_id in added_containers:
        res = await ensemble_db.add_container(container_id, db)
        responses.append(res)
    return responses


async def update_ensemble_status(status: STATUS, ensemble: Ensemble, db: Session):
    ensemble.status = status
    db.commit()
    db.refresh(ensemble)


