from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.core.database import Base

class Path(Base):
    __tablename__ = "paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"))

    # Relationships
    path_node = relationship("PathNode", back_populates="path", cascade="all, delete-orphan") # if parent is removed orphans will delete too
    unit = relationship("Unit", back_populates="path", uselist=False) # uselist: Path is child of just ONE unit

