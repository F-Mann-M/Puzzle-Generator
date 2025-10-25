# import models/libraries
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

# import form project
from app.database import get_db
from app import models, schemas
from app.services import PuzzleServices


router = APIRouter()

# create a puzzle (POST)
@router.post("/", response_model=schemas.PuzzleResponse)
def create_puzzle(
    puzzle: schemas.PuzzleCreate,
    db: Session = Depends(get_db)
):
    """Create a new puzzle entry"""
    service_create = PuzzleServices(db)
    return service_create.create_puzzle(puzzle)


# get a list of puzzle (GET)
@router.get("/", response_model=List[schemas.PuzzleResponse])
def get_puzzles(
    db: Session = Depends(get_db),
    game_mode: Optional[str] = Query(None, description="Filter by game mode"),
    model: Optional[str] = Query(None, description="Filter by model type"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    order: Optional[str] = Query("asc", description="Sort order")
):
    """Get a list of puzzles, with optional filters and sorting"""
    services = PuzzleServices(db)
    return services.get_all_puzzle(game_mode, model, sort_by, order)


# get one puzzle id
@router.get("/{puzzle_id}", response_model=schemas.PuzzleResponse)
def get_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Fetch one puzzle by ID"""
    services = PuzzleServices(db)
    return services.get_puzzle_by_id(puzzle_id)


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


# update puzzle
    # update puzzle and all related databases (nodes, units, edges)