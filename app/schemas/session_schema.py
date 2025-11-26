from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class SessionRequest(BaseModel):
    session_id: Optional[UUID] = None
    role: str
    content: str
    model: str

