from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID


class EdgeCreate(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )
    edge_index: int
    start_node_id: UUID
    end_node_id: UUID
    puzzle_id: UUID
    label: Optional[str] = "default"

# for llm generation
class EdgeGenerate(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )
    index: int
    start: int
    end: int


class EdgeRead(EdgeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class EdgeUpdate(EdgeRead):
    model_config = ConfigDict(from_attributes=True)
    pass

