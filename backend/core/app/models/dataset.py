from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Session, relationship, selectinload
from ..database import Base, get_db_session_context
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles

class Dataset(Base):
    __tablename__ = "dataset"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    data_file_path = Column(String(1024), nullable=False)
    labels_file_path = Column(String(1024), nullable=False)
    description = Column(String(2048), nullable=False)
    ammount_benign = Column(Integer, nullable=False)
    ammount_malicious = Column(Integer, nullable=False)
    dataset_type_id = Column(Integer, ForeignKey("dataset_type.id"), nullable=False)

    dataset_type = relationship('DatasetType', back_populates="dataset", lazy="selectin")


async def get_dataset_by_id(db: AsyncSession=None, dataset_id: int=None):
    stmt = select(Dataset).where(Dataset.id == dataset_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() 

async def get_all_datasets(db: AsyncSession):
    stmt = select(Dataset)
    result = await db.execute(stmt)
    return result.scalars().all()  

async def remove_dataset_by_id(db: AsyncSession, id: int):
    from ..utils import remove_directory
    dataset: Dataset = await get_dataset_by_id(db, id)
    if dataset:
        directory = "/".join(dataset.labels_file_path.split("/")[:-2])
        remove_directory(directory)
        await db.delete(dataset)
        await db.commit()
async def add_dataset(db: AsyncSession, dataset: Dataset):
        db.add(dataset)
        await db.commit() 
        await db.refresh(dataset) 