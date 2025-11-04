from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class PathCreate(BaseModel):
    unit_id: UUID
    puzzle_id: UUID

class PathRead(BaseModel):
    id: UUID
    unit_id: UUID
    puzzle_id: UUID

    class Config:
        from_attributes = True

# class UnitResponse(PathCreate):
#     id: UUID
#
#     class Config:
#         # orm_mode = True
#         from_attributes = True