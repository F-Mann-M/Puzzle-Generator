from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID

from app.schemas.path_schema import PathRead


class UnitCreate(BaseModel):
    unit_type: str
    faction: str
    puzzle_id: UUID
    path_nodes: list[int] # node indexes


class UnitGenerate(BaseModel):
    unit_type: str
    faction: str
    movement: str


class UnitRead(BaseModel):
    id: UUID
    unit_type: str
    faction: str
    path: UUID
    puzzle_id: UUID

    class Config:
        # orm_mode = True
        from_attributes = True

#
# class UnitResponse(UnitCreate):
#     id: UUID
#
#     class Config:
#         # orm_mode = True
#         from_attributes = True