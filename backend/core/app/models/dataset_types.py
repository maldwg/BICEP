from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, Session
from ..database import Base
from .dataset_types_implementation import *
import asyncio
from ..bicep_utils.models.ids_base import Alert
from ..logger import LOGGER
import importlib
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

class DatasetType(Base):
    __tablename__ = "dataset_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(String(2048), nullable=False)
    function_prefix = Column(String(128), nullable= False)

    dataset = relationship('Dataset')

    async def get_benign_and_malicious_counts(self, labels_file_text_stream):
        function_name = f"{self.function_prefix.lower()}_get_benign_and_malicious_counts_of_labels_file"
        module = self._import_dataset_module()
        LOGGER.debug(f"Using module: {module}")
        func = getattr(module, function_name)
        return await asyncio.to_thread(func, labels_file_text_stream)

    async def get_positives_and_negatives_from_dataset(self, dataset, alerts: list):
        function_name = f"{self.function_prefix.lower()}_get_positives_and_negatives_from_dataset"
        module = self._import_dataset_module()
        func = getattr(module, function_name)
        return await asyncio.to_thread(func, dataset, alerts)

    def _import_dataset_module(self):
        """
        Dynamically imports the correct module based on function_prefix.
        Uses relative import within the 'models' package.
        """
        # in the container the code is injected as backend, not as app, therefor backend.models.... 
        module_name = f"backend.models.dataset_types_implementation.{self.function_prefix.lower()}" 
        
        try:
            module = importlib.import_module(module_name)
            return module
        except ModuleNotFoundError as e:
            LOGGER.error(f"Module {module_name} not found: {e}")
            raise

async def get_dataset_type_by_id(db: AsyncSession, id: int):
    stmt = select(DatasetType).where(DatasetType.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
    
async def get_all_dataset_types(db: AsyncSession):
    stmt = select(DatasetType)
    result = await db.execute(stmt)
    return result.scalars().all()

