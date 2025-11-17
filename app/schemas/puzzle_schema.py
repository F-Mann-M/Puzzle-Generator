from pydantic import BaseModel
from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime

from app.schemas.unit_schema import UnitGenerate, UnitRead
from app.schemas.edge_schema import EdgeGenerate, EdgeRead
from app.schemas.node_schema import NodeRead, NodeGenerate

# Data sent by user
class PuzzleCreate(BaseModel):
    name: str
    model: str
    game_mode: str
    coins: Optional[int]
    nodes: List[dict]
    edges: List[dict]
    units: List[dict]
    description: Optional[str]


# Data sent from user to MML
class PuzzleGenerate(BaseModel):
    name: str
    model: str
    game_mode: str
    node_count: Optional[int]
    edge_count: Optional[int]
    turns: Optional[int]
    units: list[dict]


class PuzzleLLMResponse(BaseModel):
    nodes: List[NodeGenerate]
    edges: List[EdgeGenerate]
    units: List[UnitGenerate]
    coins: int | None = 5


class PuzzleRead(PuzzleCreate):
    id: UUID
    created_at: datetime
    nodes: List[NodeRead]
    edges: List[EdgeRead]
    coins: Optional[int]


class PuzzleUpdate(PuzzleCreate):
    name: Optional[str]
    model: Optional[str]
    enemy_count: Optional[int]
    player_unit_count: Optional[int]
    game_mode: Optional[str]
    node_count: Optional[int]
    edge_count: Optional[int]
    description: Optional[str]
    units: List[UnitRead]
    coins: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True # read directly form SQLAlchemy objects (Pydantic)
