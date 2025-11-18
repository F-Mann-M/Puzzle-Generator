from pydantic import BaseModel
from uuid import UUID


class EdgeCreate(BaseModel):
    edge_index: int
    start_node_id: UUID
    end_node_id: UUID
    puzzle_id: UUID
    label: str

# for llm generation
class EdgeGenerate(BaseModel):
    index: int
    start: int
    end: int


class EdgeRead(EdgeCreate):
    id: UUID

class EdgeUpdate(EdgeRead):
    pass

    class Config:
        from_attributes = True
