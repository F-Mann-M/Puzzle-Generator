from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID


class Node(Base):
    __tablename__ = "nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_index = Column(Integer, nullable=False)
    x_position = Column(Integer, nullable=False)
    y_position = Column(Integer, nullable=False)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("puzzles.id"), nullable=False)

    # Back-reference to parent puzzle
    puzzle = relationship("Puzzle", back_populates="nodes")
