# import moduls/libraries
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pyexpat.errors import messages
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pathlib import Path

# import form project
from app.database import get_db
from app import models, schemas
from app.services import PuzzleServices


# create Jinja2 template engine
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()

# load puzzle builder
@router.get("/create-puzzle", response_class=HTMLResponse)
async def show_create_puzzle(request: Request):
    return templates.TemplateResponse("create-puzzle.html", {"request": request})

# create a puzzle (POST)
@router.post("/", response_class=HTMLResponse)
async def create_puzzle(
        db: Session = Depends(get_db),
        name: str = Form(...),
        model: str = Form(...),
        enemy_count: int = Form(...),
        player_unit_count: int = Form(...),
        game_mode: str = Form(...),
        node_count: int = Form(...),
        turns: int = Form(...),

):
    """Create a new puzzle entry"""
    service_create = PuzzleServices(db)
    puzzle_data = schemas.PuzzleCreate(
        name = name,
        model = model,
        enemy_count= enemy_count,
        player_unit_count= player_unit_count,
        game_mode= game_mode,
        node_count= node_count,
        coins= turns # dummy. this will be changed
    )
    puzzle = service_create.create_puzzle(puzzle_data)
    return RedirectResponse(url=f"/puzzles/{puzzle.id}", status_code=303)


# get a list of puzzle (GET)
@router.get("/")
async def get_puzzles(
    request: Request,
    db: Session = Depends(get_db),
    name: Optional[str] = Query(None, description="Filter by name"),
    game_mode: Optional[str] = Query(None, description="Filter by game mode"),
    model: Optional[str] = Query(None, description="Filter by model type"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    order: Optional[str] = Query("asc", description="Sort order")
):
    """Get a list of puzzles, with optional filters and sorting"""
    services = PuzzleServices(db)
    puzzles = services.get_all_puzzle(name, game_mode, model, sort_by, order)
    return templates.TemplateResponse("puzzles.html", {"request": request, "puzzles": puzzles})


# get one puzzle id
@router.get("/{puzzle_id}", response_class=HTMLResponse)
async def get_puzzle(request: Request, puzzle_id: UUID, db: Session = Depends(get_db)):
    """Fetch one puzzle by ID"""
    services = PuzzleServices(db)
    puzzle = services.get_puzzle_by_id(puzzle_id)
    return templates.TemplateResponse("puzzle-details.html", {"request": request, "puzzle": puzzle})


# delete puzzle with post to avoid Java-Script
@router.post("/delete/{puzzle_id}/", status_code=204)
async def delete_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Delete a puzzle"""
    services = PuzzleServices(db)
    services.delete_puzzle(puzzle_id)
    return RedirectResponse(url="/puzzles", status_code=303)


# API Delete Request - currently not in use
@router.delete("/{puzzle_id}", status_code=200)
async def delete_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Delete a puzzle"""
    services = PuzzleServices(db)
    services.delete_puzzle(puzzle_id)
    return {"detail": f"Puzzle {puzzle_id} deleted"}

# update puzzle
    # update puzzle and all related databases (nodes, units, edges)