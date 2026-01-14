from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey


from app.core.database import Base
from uuid import uuid4

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    is_working = Column(Boolean, nullable=False, default=False)
    feedback = Column(String)
    rating = Column(Integer)
    difficulty = Column(Integer)
    puzzle_id  = Column(UUID(as_uuid=True), ForeignKey("puzzles.id"), nullable=False)

    puzzle = relationship("Puzzle", back_populates="feedback")