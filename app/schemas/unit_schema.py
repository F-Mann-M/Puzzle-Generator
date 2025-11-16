from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID

from app.schemas.node_schema import NodeGenerate



class UnitCreate(BaseModel):
    type: str
    faction: str
    puzzle_id: UUID
    path_nodes: list[int] # node indexes


class UnitGenerate(BaseModel):
    type: str
    faction: str
    path: List[int]



class UnitRead(BaseModel):
    id: UUID
    unit_type: str
    faction: str
    path: UUID
    puzzle_id: UUID

    class Config:
        from_attributes = True

#
# class UnitResponse(UnitCreate):
#     id: UUID
#
#     class Config:
#         # orm_mode = True
#         from_attributes = True