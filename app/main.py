from fastapi import FastAPI
from app.routers import puzzle_routers
from app.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

# create FastAPI
app = FastAPI(title="Puzzle Generator API", version="1.0")

# get routers
app.include_router(puzzle_routers.router, prefix="/puzzles", tags=["Puzzles"])
