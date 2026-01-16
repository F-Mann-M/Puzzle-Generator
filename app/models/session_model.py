from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import relationship


from app.core.database import Base
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic_name = Column(String)
    puzzle_id = Column(UUID, ForeignKey("puzzles.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    puzzle = relationship("Puzzle", back_populates="sessions")
    messages = relationship("Message", back_populates="sessions", cascade="all, delete-orphan")

