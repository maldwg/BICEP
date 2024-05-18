from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base

class IdsTool(Base):
    __tablename__ = "ids_tool"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    ids_type = Column(String(64), nullable=False)
    analysis_method = Column(String(64), nullable=False)

    containers = relationship("IdsContainer", back_populates="ids_tool")