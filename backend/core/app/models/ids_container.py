import asyncio
from http.client import HTTPResponse
import json
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, func, distinct
from sqlalchemy.orm import relationship, Session


from .ids_tool import get_ids_by_id
# important, otherwise error when getting all ensemble
from .ensemble_ids import *
from ..docker import *
from ..utils import STATUS, start_network_analysis, start_static_analysis, stop_analysis, parse_response_for_triggered_analysis
from ..validation.models import IdsContainerUpdate, NetworkAnalysisData
import uuid
from ..database import Base
from ..logger import LOGGER


class IdsContainer(Base):
    __tablename__ = "ids_container"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False) 
    port = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    description = Column(String(2048))
    stream_metric_task_id = Column(String(64))
    configuration_id = Column(Integer, ForeignKey("configuration.id"))
    ids_tool_id = Column(Integer, ForeignKey("ids_tool.id"))
    ruleset_id = Column(Integer, ForeignKey("configuration.id"))
    host_system_id = Column(Integer, ForeignKey("docker_host_system.id"))

    host_system = relationship('DockerHostSystem', back_populates='container')
    configuration = relationship('Configuration', back_populates='container', foreign_keys=[configuration_id])
    ids_tool = relationship('IdsTool', back_populates='container')
    ensemble_ids = relationship('EnsembleIds', back_populates='container', cascade="all, delete")
    ruleset = relationship('Configuration', back_populates='containerRuleset', foreign_keys=[ruleset_id])


    async def setup(self, db):
        from .configuration import get_config_by_id
        ids_tool = get_ids_by_id(db, self.ids_tool_id)
        self.name = f"{ids_tool.name}-{self.port}"
        config = get_config_by_id(db, self.configuration_id)
        rulseset = None
        if ids_tool.requires_ruleset:
            rulseset = get_config_by_id(db, self.ruleset_id)

        db.add(self)
        db.commit()
        db.refresh(self)
        try:
            await start_docker_container(self, ids_tool, config, rulseset)
            
        except Exception as e:
            print(e)
            db.delete(self)
            db.commit()
            db.refresh(self)

        # set statu to idle again after finish setup
        self.status = STATUS.IDLE.value
        db.commit()
        db.refresh(self)

    async def teardown(self, db):
        try:
            await remove_docker_container(self)
        except Exception as e:
            print(e)
        db.delete(self)
        db.commit()

    async def update_config(self, config_id, db):
        from .configuration import Configuration
        config_file: Configuration = db.query(Configuration).filter(Configuration.id == config_id).first()
        await inject_config(self, config_file)

    async def update_ruleset(self, ruleset_id, db):
        from  .configuration import Configuration
        ruleset_file: Configuration = db.query(Configuration).filter(Configuration.id == ruleset_id).first()
        await inject_ruleset(self, ruleset_file)

    async def start_static_analysis(self, form_data, dataset):
        response: HTTPResponse = await start_static_analysis(self, form_data, dataset)
        return response
    
    async def start_network_analysis(self, data):
        response = await start_network_analysis(self, data)
        return response
    
    async def stop_analysis(self):
        result = await stop_analysis(self)
        return result

    async def start_metric_collection(self, db, stream_metric_tasks):
        task_id = str(uuid.uuid4())
        self.stream_metric_task_id = task_id
        task = asyncio.create_task(start_metric_stream(container=self))
        stream_metric_tasks[task_id] = task
        db.commit()
        db.refresh(self)
        return f"started metric collection for container {self.id}"
    
    async def stop_metric_collection(self, db, stream_metric_tasks):
        if not self.stream_metric_task_id:
            # skip the container if there is no streaming task happening for it, e.g. an analysis hasn't been startedd
            return f"Could not stop metric collection for container {self.id}; No stream started"
        try:
            print(stream_metric_tasks)
            print(self.stream_metric_task_id)
            await stop_metric_stream(stream_metric_tasks=stream_metric_tasks, task_id=self.stream_metric_task_id, container=self)
            del stream_metric_tasks[self.stream_metric_task_id]
        except KeyError as e:
            # set to none, because this indicates that the metric task has either been canceled or the server reloaded, 
            # #either way the ID is lost in the dict, hence remove it also from the object
            self.stream_metric_task_id = None
            db.commit()
            db.refresh(self)
            print(f"Could not stop task id {self.stream_metric_task_id} in container {self.id}, skipping cancellation of the task")
            return f"Could not stop task id {self.stream_metric_task_id} in container {self.id}, skipping cancellation of the task"
        self.stream_metric_task_id = None
        db.commit()
        db.refresh(self)
        return f"stopped metric collection for container {self.id}"
    
    async def is_busy(self):
        if self.status == STATUS.ACTIVE.value:
            return True
        else:
            return False
        
    def get_container_http_url(self):
        if "Core" in self.host_system.name or self.host_system.host == "localhost":
            core_host = get_core_host()
            container_host_url = f"http://{core_host}:{self.port}"
        else:
            container_host_url = f"http://{self.host_system.host}:{self.port}"
        return container_host_url
    
    async def is_available(self):
        return await check_container_health(self)
    
def get_container_by_id(db: Session, id: int):
    return db.query(IdsContainer).filter(IdsContainer.id == id).first()
    

def get_all_container(db: Session):
    return db.query(IdsContainer).all()

def remove_container_by_id(db: Session, id):
    container = get_container_by_id(db, id)
    db.delete(container)
    db.commit()

async def update_container(container: IdsContainerUpdate, db: Session):
    container_db: IdsContainer = db.query(IdsContainer).filter(IdsContainer.id == container.id).first()
    old_config_id = container_db.configuration_id
    new_config_id = container.configuration_id
    
    if old_config_id != new_config_id:
        await container_db.update_config(new_config_id, db)
    
    old_ruleset_id = container_db.ruleset_id
    new_ruleset_id = container.ruleset_id

    if old_ruleset_id != new_config_id and new_ruleset_id != None:
        await container_db.update_ruleset(new_ruleset_id, db)    

    for key, value in container.dict().items():
        setattr(container_db, key, value)
    db.commit()
    db.refresh(container_db)

async def update_container_status(status: STATUS, container: IdsContainer, db: Session):
    container.status = status
    db.commit()
    db.refresh(container)

