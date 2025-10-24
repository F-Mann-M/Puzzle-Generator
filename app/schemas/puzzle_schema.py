from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


# Data sent by user/AI
class PuzzleCreate(BaseModel):
    model: str
    enemy_count: int
    player_unit_count: int
    game_mode: str
    node_count: int
    coins: Optional[int]

# Data returns by API
class PuzzleResponse(PuzzleCreate):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True # read directly form SQLAlchemy objects (Pydantic)