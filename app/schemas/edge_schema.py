from pydantic import BaseModel
from uuid import UUID

from app.schemas import NodeGenerate


class EdgeCreate(BaseModel):
    edge_index: int
    start_node_id: UUID
    end_node_id: UUID
    puzzle_id: UUID

# for llm generation
class EdgeGenerate(BaseModel):
    edge_index: int
    start_node_index: NodeGenerate
    end_node_index: NodeGenerate


class EdgeRead(EdgeCreate):
    id: UUID


    class Config:
        from_attributes = True
