from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID


class Edge(Base):
    __tablename__ = "edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    edge_index = Column(Integer, nullable=False)
    start_node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False)
    end_node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("puzzles.id"), nullable=False)

    # Relationships
    puzzle = relationship("Puzzle", back_populates="edges")
    start_node = relationship("Node", foreign_keys=[start_node_id], back_populates="start_edges")
    end_node = relationship("Node", foreign_keys=[end_node_id], back_populates="end_edges")
    # path = relationship("Path") # Relationship Path many-to-one Node