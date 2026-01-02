from pydantic import BaseModel, ConfigDict
from uuid import UUID


class NodeCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    index: int
    x_position: int
    y_position: int
    puzzle_id: UUID


# for llm generation
class NodeGenerate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    index: int
    x: float
    y: float


class NodeRead(NodeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class NodeUpdate(NodeRead):
    model_config = ConfigDict(from_attributes=True)
    pass
