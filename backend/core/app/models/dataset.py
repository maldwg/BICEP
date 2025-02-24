from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Session, relationship
from ..database import Base

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

    dataset_type = relationship('DatasetType', back_populates="dataset")

def get_dataset_by_id(db: Session, dataset_id: int):
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()
    

def get_all_datasets(db: Session):
    return db.query(Dataset).all()

def remove_dataset_by_id(db: Session, id: int):
    from ..utils import remove_directory
    dataset: Dataset = get_dataset_by_id(db, id)
    directory = "/".join(dataset.labels_file_path.split("/")[:-2])
    remove_directory(directory)
    db.delete(dataset)
    db.commit()

def add_dataset(db: Session, dataset: Dataset):
    db.add(dataset)
    db.commit()