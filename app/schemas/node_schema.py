from pydantic import BaseModel
from uuid import UUID


class NodeBase(BaseModel):
    node_index: int
    x_position: int
    y_position: int

class NodeCreate(NodeBase):
    """schema used when creating nodes after ID is generated"""
    pass

class NodeResponse(NodeBase):
    id: UUID

    class Config:
        orm_mode = True