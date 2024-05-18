from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Blob
from sqlalchemy.orm import relationship

from ..database import Base

class Configuration(Base):
    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True)
    configuration = Column(Blob, nullable=False)
    description = Column(String(2048))

    containers = relationship("IdsContainer", back_populates="configuration")