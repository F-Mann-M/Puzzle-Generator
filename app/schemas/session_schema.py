from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class SessionRequest(BaseModel):
    session_id: Optional[UUID] = None
    content: str
    model: str
    puzzle_id: Optional[UUID] = None

class ChatFromRequest(BaseModel):
    session_id: Optional[UUID] = None
    content: str
    model: str

