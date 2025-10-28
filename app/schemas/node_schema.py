from pydantic import BaseModel
from uuid import UUID


class NodeCreate(BaseModel):
    node_index: int
    x_position: int
    y_position: int


class NodeResponse(NodeCreate):
    id: UUID

    class Config:
        orm_mode = True