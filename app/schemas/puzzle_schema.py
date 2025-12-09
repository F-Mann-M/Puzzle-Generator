from pydantic import BaseModel
from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime

from app.schemas.unit_schema import UnitGenerate, UnitRead, UnitUpdate
from app.schemas.edge_schema import EdgeGenerate, EdgeRead, EdgeUpdate
from app.schemas.node_schema import NodeRead, NodeGenerate, NodeUpdate
from app.schemas.path_nodes_schema import PathNodesUpdate

# Data sent by user
class PuzzleCreate(BaseModel):
    name: str
    model: str
    game_mode: str
    coins: Optional[int]
    nodes: List[dict]
    edges: List[dict]
    units: List[dict]
    description: Optional[str] = ""
    is_working: Optional[bool] = False


# Data sent from user to MML
class PuzzleGenerate(BaseModel):
    name: str
    model: str
    game_mode: str
    node_count: Optional[int]
    edge_count: Optional[int]
    turns: Optional[int]
    units: list[dict]
    description: Optional[str] = ""


class PuzzleLLMResponse(BaseModel):
    nodes: List[NodeGenerate]
    edges: List[EdgeGenerate]
    units: List[UnitGenerate]
    coins: int | None = 5
    description: Optional[str] = ""


class PuzzleRead(PuzzleCreate):
    id: UUID
    created_at: datetime
    nodes: List[NodeRead]
    edges: List[EdgeRead]
    coins: Optional[int]


class PuzzleUpdate(PuzzleCreate):
    enemy_count: Optional[int]
    player_unit_count: Optional[int]
    node_count: Optional[int]
    edge_count: Optional[int]
    description: Optional[str]
    coins: Optional[int]
    updated_at: datetime
    units: List[UnitUpdate]
    nodes: List[NodeUpdate]
    edges: List[EdgeUpdate]
    path_nodes: List[PathNodesUpdate]

    class Config:
        from_attributes = True # read directly form SQLAlchemy objects (Pydantic)
