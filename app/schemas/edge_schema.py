from pydantic import BaseModel
from uuid import UUID


class EdgeCreate(BaseModel):
    edge_index: int
    start_node: int
    end_node: int


class EdgeResponse(EdgeCreate):
    id: UUID
    edge_index: int
    start_node_id: UUID
    end_node_id: UUID

    class Config:
        orm_mode = True
