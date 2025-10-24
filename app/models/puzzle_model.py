from sqlalchemy import Column, Integer, String, func, DateTime
from app.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID

class Puzzle(Base):
    __tablename__ = "puzzles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model = Column(String, nullable=False)
    enemy_count = Column(Integer) # since there is a unit table this makes no sense, or?
    player_unit_count = Column(Integer, nullable=False) # same gose for player_units
    game_mode = Column(String, nullable=False)
    node_count = Column(Integer, nullable=False)
    coins = Column(Integer, nullable=False) # coins equal turns
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


