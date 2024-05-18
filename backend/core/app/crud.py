from sqlalchemy.orm import Session
from .models import ids_container, configuration, ids_tool
from .validation import models

def get_config_by_id(db: Session, config_id: int):
    return db.query(configuration.Configuration).filter(configuration.id == config_id).first()
    
def get_ids_by_id(db: session, ids_id: int):
    return db.query(ids_tool.IdsTool).filter(ids_tool.id == ids_id).first()
