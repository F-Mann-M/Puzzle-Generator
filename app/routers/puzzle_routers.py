# import moduls/libraries
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from pathlib import Path
import json


# import form project
from app.core.database import get_db
from app import models
from app.schemas import PuzzleCreate, PuzzleGenerate
from app.services import PuzzleServices
from app.visualization import generate_puzzle_visualization, generate_preview_visualization


# create Jinja2 template engine
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()

# load puzzle builder
@router.get("/create-puzzle", response_class=HTMLResponse)
async def show_create_puzzle(request: Request):
    return templates.TemplateResponse("create-puzzle.html", {"request": request})


# Create puzzle by you own
@router.post("/", response_class=HTMLResponse)
async def create_puzzle(puzzle: PuzzleCreate, db: Session = Depends(get_db)):
    services = PuzzleServices(db)
    new_puzzle = services.create_puzzle(puzzle)
    return RedirectResponse(url=f"/puzzles/{new_puzzle.id}", status_code=303)


# Load puzzle generator
@router.get("/generate", response_class=HTMLResponse)
async def show_generate_puzzle(request: Request):
     return templates.TemplateResponse("generate-puzzle.html", {"request": request})


# Generate puzzle (LLM Endpoint)
@router.post("/generate")
async def generate_puzzle(puzzle_generate: PuzzleGenerate, db: Session = Depends(get_db)):
    """Takes in json data from front-end, generates puzzle data and stores puzzle to database."""
    services = PuzzleServices(db)
    puzzle_generated = await services.generate_puzzle(puzzle_generate)
    new_puzzle = services.create_puzzle(puzzle_generated)
    return RedirectResponse(url=f"/puzzles/{new_puzzle.id}", status_code=303)


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


# API Delete Request
@router.delete("/{puzzle_id}", status_code=200)
async def delete_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Delete a puzzle"""
    services = PuzzleServices(db)
    services.delete_puzzle(puzzle_id)
    return {"detail": f"Puzzle {puzzle_id} deleted"}


# Get puzzle by id
@router.get("/{puzzle_id}", response_class=HTMLResponse)
async def get_puzzle(request: Request, puzzle_id: UUID, db: Session = Depends(get_db)):
    """Fetch one puzzle by ID"""
    services = PuzzleServices(db)
    puzzle = services.get_puzzle_by_id(puzzle_id)
    return templates.TemplateResponse("puzzle-details.html", {"request": request, "puzzle": puzzle})


@router.get("/{puzzle_id}/update", response_class=HTMLResponse)
def show_update_puzzle(request: Request, puzzle_id: UUID, db: Session = Depends(get_db)):
    services = PuzzleServices(db)
    puzzle = services.get_puzzle_by_id(puzzle_id)
    return templates.TemplateResponse("update-puzzle.html", {"request": request, "puzzle": puzzle})


# Puzzle Visualization
@router.get("/{puzzle_id}/visualization", response_class=HTMLResponse)
async def visualize_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    puzzle = db.query(models.Puzzle).filter(models.Puzzle.id == puzzle_id).first()
    if not puzzle:
        return HTMLResponse("<h3>Puzzle not found</h3>", status_code=404)

    fig = generate_puzzle_visualization(puzzle)
    html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    return HTMLResponse(content=html)


@router.post("/preview")
async def preview_puzzle(config: dict):
    fig = generate_preview_visualization(config)
    return JSONResponse(content=json.loads(fig.to_json()))

