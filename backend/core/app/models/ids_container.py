from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class IdsContainer(Base):
    __tablename__ = "ids_container"

    id = Column(Integer, primary_key=True)
    url = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    description = Column(String(2048))
    configuration_id = Column(Integer, ForeignKey("configuration.id"))
    ids_tool_id = Column(Integer, ForeignKey("ids_tool.id"))

    configuration = relationship('Configuration', back_populates='containers')
    ids_tool = relationship('IdsTool', back_populates='containers')



