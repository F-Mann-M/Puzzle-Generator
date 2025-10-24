# import models/libraries
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

# import form project
from app.database import get_db
from app import models, schemas


router = APIRouter()

# create a puzzle (POST)
@router.post("/", response_model=schemas.PuzzleResponse)
def create_puzzle(puzzle: schemas.PuzzleCreate, db: Session = Depends(get_db)):
    """Create a new puzzle entry"""
    db_puzzle = models.Puzzle(**puzzle.model_dump()) # converts Pydantic object (Puzzle model) into a dict and unpacks dict into keyword arguments
    db.add(db_puzzle)
    db.commit()
    db.refresh(db_puzzle)
    return db_puzzle

# get a list of puzzle (GET)
@router.get("/", response_model=List[schemas.PuzzleResponse])
def get_puzzles(
    db: Session = Depends(get_db), # obens the database session and injects it into the function
    game_mode: Optional[str] = Query(None, description="Filter by game mode"),
    model: Optional[str] = Query(None, description="Filter by model type"),
    sort_by: Optional[str] = Query(None, description="Sort field: model, created_at, etc."),
    order: Optional[str] = Query("asc", description="Sort order: asc or desc")
    ):
    """Get a list of puzzles, with optional filters and sorting"""
    query = db.query(models.Puzzle)

    if game_mode:
        query = query.filter(models.Puzzle.game_mode == game_mode)
    if model:
        query = query.filter(models.Puzzle.model == model)

    if sort_by:
        sort_column = getattr(models.Puzzle, sort_by, None)
        if sort_column:
            query = query.order_by(sort_column.desc() if order == "desc" else sort_column.asc())

    puzzles = query.all()
    return puzzles


# get one puzzle id
@router.get("/{puzzle_id}", response_model=schemas.PuzzleResponse)
def get_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Fetch one puzzle by ID"""
    puzzle = db.query(models.Puzzle).filter(models.Puzzle.id == puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return puzzle


# delete puzzle
@router.delete("/{puzzle_id}", status_code=204)
def delete_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Delete a puzzle"""
    puzzle = db.query(models.Puzzle).filter(models.Puzzle.id == puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    db.delete(puzzle)
    db.commit()
    return {"detail": "Puzzle deleted"}
