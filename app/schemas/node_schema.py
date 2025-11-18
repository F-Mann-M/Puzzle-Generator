from pydantic import BaseModel
from uuid import UUID


class NodeCreate(BaseModel):
    node_index: int
    x_position: int
    y_position: int
    puzzle_id: UUID

# for llm generation
class NodeGenerate(BaseModel):
    index: int
    x: float
    y: float


class NodeRead(NodeCreate):
    id: UUID


class NodeUpdate(NodeRead):
    pass

    class Config:
        # orm_mode = True
        from_attributes = True