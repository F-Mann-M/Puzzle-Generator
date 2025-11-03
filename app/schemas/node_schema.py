from pydantic import BaseModel
from uuid import UUID


class NodeCreate(BaseModel):
    node_index: int
    x_position: int
    y_position: int
    puzzle_id: UUID


class NodeResponse(NodeCreate):
    id: UUID

    class Config:
        # orm_mode = True
        from_attributes = True