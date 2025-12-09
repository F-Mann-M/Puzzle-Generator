from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID


class ChatFromRequest(BaseModel):
    session_id: Optional[UUID] = None
    content: str
    model: str

    @field_validator('session_id', mode='before') # runs before Pydantic type conversion. Recives row input
    @classmethod
    def empty_str_to_none(cls, value):
        """Convert empty string to None for session_id"""
        if value == "" or value is None:
            return None
        return value
