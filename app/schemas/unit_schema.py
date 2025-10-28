from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class UnitBase(BaseModel):
    unit_type: str
    movement: Optional[str] = None
    faction: str

class UnitCreate(UnitBase):
    """schema used when creating units after ID is generated"""
    pass

class UnitResponse(UnitBase):
    id: UUID

    class Config:
        orm_mode = True