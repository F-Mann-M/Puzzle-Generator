from pydantic import BaseModel
from uuid import UUID


class EdgeCreate(BaseModel):
    edge_index: int
    start_node_id: UUID
    end_node_id: UUID
    puzzle_id: UUID


class EdgeResponse(EdgeCreate):
    id: UUID

    class Config:
        # orm_mode = True
        from_attributes = True
