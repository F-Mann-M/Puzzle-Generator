# import moduls/libraries
from fastapi import APIRouter, Depends, Query, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from pathlib import Path



# import form project
from app.core.database import get_db
from app.schemas import PuzzleCreate, PuzzleGenerate, SessionRequest
from app.services import PuzzleServices


# create Jinja2 template engine
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()

# load puzzle builder
@router.get("/create-puzzle", response_class=HTMLResponse)
async def show_create_puzzle(request: Request):
    """Show create puzzle page"""
    return templates.TemplateResponse("create-puzzle.html", {"request": request})


# load chat
@router.get("/chat", response_class=HTMLResponse)
async def show_chat(request: Request):
    """Get chat page"""
    return templates.TemplateResponse("chat.html", {"request": request})


# Chat:
@router.post("/chat", response_class=HTMLResponse)
async def chat(session_data: SessionRequest, db: Session = Depends(get_db)
):
    """Chat with the AI"""
    print("this is chat content: ", session_data.message, session_data.model)

    services = PuzzleServices(db)
    response = await services.chat(session_data.model, session_data.content)
    user_msg = f'<div class="user-msg" style="margin: 10px 0; padding: 10px; background-color: #e3f2fd; border-radius: 5px;"><strong>You:</strong> {session_data.content}</div>'
    ai_msg = f'<div class="ai-msg" style="margin: 10px 0; padding: 10px; background-color: #f1f8e9; border-radius: 5px;"><strong>Rudolfo:</strong> {response}</div>'
    return HTMLResponse(content=user_msg + ai_msg)

# Create puzzle
@router.post("/", response_class=HTMLResponse)
async def create_puzzle(puzzle: PuzzleCreate, db: Session = Depends(get_db)):
    """Create a new puzzle"""
    services = PuzzleServices(db)
    new_puzzle = services.create_puzzle(puzzle)
    return RedirectResponse(url=f"/puzzles/{new_puzzle.id}", status_code=303)


# Load puzzle generator
@router.get("/generate", response_class=HTMLResponse)
async def show_generate_puzzle(request: Request):
    """Show generate puzzle page"""
    return templates.TemplateResponse("generate-puzzle.html", {"request": request})


# Generate puzzle (LLM Endpoint)
@router.post("/generate")
async def generate_puzzle(puzzle_generate: PuzzleGenerate, db: Session = Depends(get_db)):
    """Generate a new puzzle"""
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
@router.delete("/{puzzle_id}/delete", status_code=204)
async def delete_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Delete a puzzle"""
    services = PuzzleServices(db)
    services.delete_puzzle(puzzle_id)
    return HTMLResponse(content="", status_code=200)


# Get puzzle by id
@router.get("/{puzzle_id}", response_class=HTMLResponse)
async def get_puzzle(request: Request, puzzle_id: UUID, db: Session = Depends(get_db)):
    """Fetch one puzzle by ID"""
    services = PuzzleServices(db)
    puzzle = services.get_puzzle_by_id(puzzle_id)
    return templates.TemplateResponse("puzzle-details.html", {"request": request, "puzzle": puzzle})


@router.get("/{puzzle_id}/update", response_class=HTMLResponse)
def show_update_puzzle(request: Request, puzzle_id: UUID, db: Session = Depends(get_db)):
    """Show update puzzle page"""
    services = PuzzleServices(db)
    puzzle = services.get_puzzle_by_id(puzzle_id)
    return templates.TemplateResponse("update-puzzle.html", {"request": request, "puzzle": puzzle})

# Serialize puzzle data to JSON for puzzle visualization
@router.get("/{puzzle_id}/data", response_class=JSONResponse)
async def get_puzzle_data(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Get puzzle data as JSON for visualization"""
    services = PuzzleServices(db)
    puzzle_data = services.serialize_puzzle(puzzle_id) # Serialize puzzle data to JSON
    return JSONResponse(content=puzzle_data)


