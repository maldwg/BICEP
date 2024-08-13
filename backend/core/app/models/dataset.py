from sqlalchemy import Column, Integer, String
from sqlalchemy.types import BLOB
from sqlalchemy.orm import Session, defer

from ..database import Base

class Dataset(Base):
    __tablename__ = "dataset"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    pcap_file = Column(BLOB, nullable=False)
    labels_file = Column(BLOB, nullable=False)
    description = Column(String(2048), nullable=False)
    ammount_benign = Column(Integer, nullable=False)
    ammount_malicious = Column(Integer, nullable=False)

def get_dataset_by_id(db: Session, dataset_id: int):
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()
    

def get_all_datasets(db: Session):
    return db.query(Dataset).all()

def get_all_datasets_with_dummy_data(db: Session):
    datasets = db.query(Dataset).options(defer(Dataset.pcap_file), defer(Dataset.labels_file)).all()
    for dataset in datasets:
        dataset.pcap_file = b""  # Set to empty byte string as dummy value
        dataset.labels_file = b""  # Set to empty byte string as dummy value
    return datasets

def remove_dataset_by_id(db: Session, id: int):
    dataset = get_dataset_by_id(db, id)
    db.delete(dataset)
    db.commit()

def add_dataset(db: Session, dataset: Dataset):
    db.add(dataset)
    db.commit()