from uuid import uuid4
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class PathNode(Base):
    __tablename__ = "path_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    path_id = Column(UUID(as_uuid=True), ForeignKey("paths.id", ondelete="CASCADE")) # if there is no path with id, delete this PathNode
    node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id"))
    order_index = Column(Integer, nullable=False)
    node_index = Column(Integer) # for visualization in puzzle details

    # Relationship
    path = relationship("Path", back_populates="path_node")
    node = relationship("Node", back_populates="path_node")