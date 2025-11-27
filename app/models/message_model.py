from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False) # Goetz (user), Rudolfo (assistant), Adelheid (assistant)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    sessions = relationship("Session", back_populates="messages")

