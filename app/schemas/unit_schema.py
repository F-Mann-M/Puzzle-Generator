from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class UnitCreate(BaseModel):
    unit_type: str
    faction: str
    puzzle_id: UUID
    path_nodes: list[int] # node indexes

class UnitResponse(UnitCreate):
    id: UUID

    class Config:
        orm_mode = True