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
    enemy_count = Column(Integer) # since there is a unit table this makes no sense, or?
    player_unit_count = Column(Integer, nullable=False) # same goes for player_units
    game_mode = Column(String, nullable=False)
    node_count = Column(Integer, nullable=False)
    coins = Column(Integer, nullable=False) # coins equal turns
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationship: one puzzle < many units
    units = relationship("Unit", back_populates="puzzle", cascade="all, delete-orphan")


