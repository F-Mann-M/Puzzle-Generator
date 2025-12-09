from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID


class Node(Base):
    __tablename__ = "nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_index = Column(Integer, nullable=False)
    x_position = Column(Integer, nullable=False)
    y_position = Column(Integer, nullable=False)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("puzzles.id"), nullable=False)

    # Relationship
    puzzle = relationship("Puzzle", back_populates="nodes")

    start_edges = relationship("Edge", foreign_keys="[Edge.start_node_id]", back_populates="start_node")
    end_edges = relationship("Edge", foreign_keys="[Edge.end_node_id]", back_populates="end_node")

    path_node = relationship("PathNode", back_populates="node")