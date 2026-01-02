from typing import List, Any, Optional
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID


class UnitCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    unit_type: str
    faction: str
    puzzle_id: UUID
    path_nodes: Optional[list[int]] = [] # node indexes

    @field_validator("path_nodes", mode="before")
    @classmethod
    def transform_path_to_indexes(cls, v: Any) -> List[int]:
        # If 'v' is an SQLAlchemy ist of Path objects
        if isinstance(v, list) and len(v) > 0:
            # Check if items in the list have a node_index attribute
            if hasattr(v[0], 'node_index'):
                return [path_obj.node_index for path_obj in v]
        return v if isinstance(v, list) else []

class UnitGenerate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: str
    faction: str
    path: List[int]


class UnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str
    faction: str
    path: UUID
    puzzle_id: UUID


class UnitUpdate(UnitCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str

