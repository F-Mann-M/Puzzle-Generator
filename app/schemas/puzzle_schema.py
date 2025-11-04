from pydantic import BaseModel
from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime

from app.schemas.unit_schema import UnitCreate, UnitGenerate
from app.schemas.node_schema import NodeCreate
from app.schemas.edge_schema import EdgeCreate

# Data sent by user
class PuzzleCreate(BaseModel):
    name: str
    model: str
    enemy_count: int
    player_unit_count: int
    game_mode: str
    node_count: int
    edge_count: int
    coins: Optional[int]

# Data sent from user to MML
class PuzzleGenerate(BaseModel):
    name: str
    model: str
    game_mode: str
    node_count: Optional[int]
    turns: Optional[int]
    enemy_count: int
    player_unit_count: int
    units: list[dict]


# Data returns by API
class PuzzleResponse(PuzzleCreate):
    id: UUID
    created_at: datetime


class PuzzleUpdate(PuzzleCreate):
    name: Optional[str]
    model: Optional[str]
    enemy_count: Optional[int]
    player_unit_count: Optional[int]
    game_mode: Optional[str]
    node_count: Optional[int]
    edge_count: Optional[int]
    coins: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True # read directly form SQLAlchemy objects (Pydantic)


# Get data
class PuzzleRead(BaseModel):
    id: UUID
    name: str
    model: str
    enemy_count: int
    player_unit_count: int
    #enemy_units: List[UnitRead]
    game_mode: str
    #nodes: List[NodeRead]
    #edges: List[EdgeRead]
    coins: Optional[int]


