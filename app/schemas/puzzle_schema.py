from pydantic import BaseModel, ConfigDict
from typing import Optional, List


from app.schemas.unit_schema import UnitGenerate, UnitCreate
from app.schemas.edge_schema import EdgeGenerate, EdgeCreate
from app.schemas.node_schema import NodeGenerate, NodeCreate


# Data sent by user
class PuzzleCreate(BaseModel):
    name: str
    model: str
    game_mode: str
    coins: Optional[int]
    nodes: List[NodeGenerate]
    edges: List[EdgeGenerate]
    units: List[UnitGenerate]
    description: Optional[str] = ""
    is_working: Optional[bool] = False

    # read SQLAlchemy object also like dicts
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid")


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

    # read SQLAlchemy object also like dicts
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class PuzzleLLMResponse(BaseModel):
    nodes: List[NodeGenerate]
    edges: List[EdgeGenerate]
    units: List[UnitGenerate]
    coins: int | None = 5
    description: Optional[str] = ""

    # read SQLAlchemy object also like dicts
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid")

# to load and convert puzzle object for llm
class PuzzleExport(PuzzleCreate):
    model_config = ConfigDict(from_attributes=True)
    nodes: List[NodeCreate]
    edges: List[EdgeCreate]
    units: List[UnitCreate]