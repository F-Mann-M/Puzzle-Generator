from typing import Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class PathCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    unit_id: UUID
    puzzle_id: UUID
