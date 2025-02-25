from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Session, relationship
from ..database import Base, get_db_session_context
from sqlalchemy.future import select

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


async def get_dataset_by_id(dataset_id: int):
    async with get_db_session_context() as db:
        stmt = select(Dataset).where(Dataset.id == dataset_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()  # Return a single row or None

async def get_all_datasets():
    async with get_db_session_context() as db:
        stmt = select(Dataset)
        result = await db.execute(stmt)
        return result.scalars().all()  # Return all results

async def remove_dataset_by_id(id: int):
    from ..utils import remove_directory
    async with get_db_session_context() as db:
        dataset: Dataset = await get_dataset_by_id(id)
        if dataset:
            directory = "/".join(dataset.labels_file_path.split("/")[:-2])
            remove_directory(directory)
            await db.delete(dataset)
            await db.commit()

async def add_dataset(dataset: Dataset):
    async with get_db_session_context() as db:
        db.add(dataset)
        await db.commit()  # Commit asynchronously
        await db.refresh(dataset)  # Refresh to get updated values