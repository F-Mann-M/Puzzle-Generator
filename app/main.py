from fastapi import FastAPI
from pydantic import BaseModel
from app.models import puzzles
from app.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Puzzle Generator API", version="1.0")

class PuzzleInput(BaseModel):
    name: str
    difficulty: int

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/")
async def create_puzzle(puzzle: PuzzleInput):
    return {"message": "Puzzle created!", "puzzle": puzzle}