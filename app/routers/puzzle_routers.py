# import moduls/libraries
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from pathlib import Path
import plotly.graph_objects as go

# import form project
from app.core.database import get_db
from app import models
from app.schemas import PuzzleCreate, PuzzleGenerate
from app.services import PuzzleServices


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
@router.get(
    "/{puzzle_id}/visualization",
    response_class=HTMLResponse,
    response_model=None
)
def visualize_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    puzzle = db.query(models.Puzzle).filter(models.Puzzle.id == puzzle_id).first()
    if not puzzle:
        return HTMLResponse("<h3>Puzzle not found</h3>", status_code=404)

    # --- Visualization logic ---
    positions = {n.id: (n.x_position, n.y_position) for n in puzzle.nodes}
    edge_x, edge_y = [], []
    for e in puzzle.edges:
        x0, y0 = positions[e.start_node_id]
        x1, y1 = positions[e.end_node_id]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", line=dict(width=2, color="#aaa"), name="Edges"
    ))

    colors = ["red", "blue", "green", "orange", "purple"]
    for i, unit in enumerate(puzzle.units):
        if not unit.path or not unit.path.path_node:
            continue
        path_nodes = sorted(unit.path.path_node, key=lambda p: p.order_index)
        xs = [positions[p.node.id][0] for p in path_nodes]
        ys = [positions[p.node.id][1] for p in path_nodes]
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers",
            line=dict(width=4, color=colors[i % len(colors)]),
            marker=dict(size=10, color=colors[i % len(colors)]),
            name=unit.unit_type or f"Unit {i+1}"
        ))

    node_x = [n.x_position for n in puzzle.nodes]
    node_y = [n.y_position for n in puzzle.nodes]
    node_labels = [n.node_index for n in puzzle.nodes]
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=node_labels, textposition="middle center",
        marker=dict(size=20, color="white", line=dict(width=2, color="black")),
        name="Nodes"
    ))

    fig.update_layout(
        title=f"Puzzle: {puzzle.name}",
        showlegend=True,
        plot_bgcolor="white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=600
    )

    html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    return HTMLResponse(content=html)

