from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class PathCreate(BaseModel):
    unit_id: UUID
    puzzle_id: UUID
