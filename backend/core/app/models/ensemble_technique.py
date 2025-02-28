from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, Session
from ..utils import combine_alerts_for_ids_in_alert_dict
from ..database import Base
from ..logger import LOGGER
from .ensemble_techniques_implementation import *
import importlib
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import os 
class EnsembleTechnique(Base):
    __tablename__ = "ensemble_technique"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(String(2048), nullable=False)
    function_name = Column(String(128), nullable=False)

    ensemble = relationship('Ensemble', back_populates='ensemble_technique', lazy="selectin")

    async def execute_technique_by_name_on_alerts(self, alerts_dict: dict, ensemble):
        module = self._import_ensemble_technique_module()
        print(module)
        func = getattr(module, self.function_name)
        common_alerts = await combine_alerts_for_ids_in_alert_dict(alerts_dict)
        return await func(common_alerts=common_alerts, ensemble=ensemble)

    def _import_ensemble_technique_module(self):
        # in the container the code is injected as backend, not as app, therefor backend.models.... 
        module_name = f"app.models.ensemble_techniques_implementation.{self.function_name.lower()}" 
        try:
            module = importlib.import_module(module_name)
            return module
        except ModuleNotFoundError as e:
            LOGGER.error(f"Module {module_name} not found: {e}")
            raise

async def get_all_ensemble_techniques(db: AsyncSession):
    stmt = select(EnsembleTechnique)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_ensemble_technique_by_id(db: AsyncSession, id: int):
    stmt = select(EnsembleTechnique).where(EnsembleTechnique.id == id)
    return await db.execute(stmt).scalar_one_or_none()
