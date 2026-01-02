from pydantic import BaseModel
from typing import Optional, List

from app.schemas.unit_schema import UnitGenerate
from app.schemas.edge_schema import EdgeGenerate
from app.schemas.node_schema import NodeGenerate

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


# Data sent from user to LLM
class PuzzleGenerate(BaseModel):
    name: str
    model: str
    game_mode: str
    node_count: Optional[int]
    edge_count: Optional[int]
    turns: Optional[int]
    units: list[dict]
    description: Optional[str] = "" # used to give further instructions related to the puzzle


class PuzzleLLMResponse(BaseModel):
    nodes: List[NodeGenerate]
    edges: List[EdgeGenerate]
    units: List[UnitGenerate]
    coins: int | None = 5
    description: Optional[str] = ""
