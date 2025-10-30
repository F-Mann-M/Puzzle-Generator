import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Path(Base):
    __tablename__ = "paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("puzzles.id"))
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"))

    puzzle = relationship("Puzzle")
    unit = relationship("Unit", back_populates="path")
    nodes = relationship("PathNode", back_populates="path", cascade="all, delete-orphan")