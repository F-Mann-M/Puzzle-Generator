from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID


class Unit(Base):
    __tablename__ = "units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    unit_type = Column(String, nullable=False)  # Grunt, Brute, Archer
    faction = Column(String, nullable=False)  # 'enemy' or 'player'
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("puzzles.id"), nullable=False)

    # Relationships
    puzzle = relationship("Puzzle", back_populates="units")
    path = relationship("Path", back_populates="unit", uselist=False, cascade="all, delete") # unlist: each unit has just one path