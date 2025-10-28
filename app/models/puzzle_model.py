from sqlalchemy import Column, Integer, String, func, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID


class Puzzle(Base):
    __tablename__ = "puzzles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    model = Column(String, nullable=False)
    enemy_count = Column(Integer)
    player_unit_count = Column(Integer, nullable=False)
    game_mode = Column(String, nullable=False)
    node_count = Column(Integer, nullable=False)
    edge_count = Column(Integer)
    coins = Column(Integer)
    turns = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationship: one puzzle < many units
    units = relationship("Unit", back_populates="puzzle", cascade="all, delete-orphan")
    nodes = relationship("Node", back_populates="puzzle", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="puzzle", cascade="all, delete-orphan")
    # path relationship
    # edge relationship


