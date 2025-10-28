# import moduls/libraries
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from pathlib import Path

# import form project
from app.database import get_db
from app import schemas
from app.services import PuzzleServices


# create Jinja2 template engine
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()

# load puzzle builder
@router.get("/create-puzzle", response_class=HTMLResponse)
async def show_create_puzzle(request: Request):
    return templates.TemplateResponse("create-puzzle.html", {"request": request})

@router.post("/", response_class=HTMLResponse)
async def create_puzzle(request: Request, db: Session = Depends(get_db)):
    # get data from form and store in dict
    form_content = await request.form()
    puzzle_config = dict(form_content)

    # Build units and nodes
    units =[]
    for key, value in puzzle_config.items():
        if key.startswith("unit_enemy_") and key.endswith("_type"):
            unit_id = key.split("_")[2] # isolates unit number
            units.append({
                "faction": "enemy",
                "unit_type": value, # Grunt, Brute
                "movement": puzzle_config.get(f"unit_enemy_{unit_id}_movement")
            })
        elif key.startswith("unit_player_") and key.endswith("_type"):
            unit_id = key.split("_")[2]
            units.append({
                "faction": "player",
                "unit_type": value,
                "movement": puzzle_config.get(f"unit_player_{unit_id}_movement")
            })

    # Build nodes
    nodes = []
    node_count = int(puzzle_config.get("node_count", 0))
    for i in range(node_count):
        x_key = f"node_{i}_x"
        y_key = f"node_{i}_y"
        if x_key in puzzle_config and y_key in puzzle_config:
            nodes.append({
                "index": i,
                "x": int(puzzle_config[x_key]),
                "y": int(puzzle_config[y_key])
            })

    # Build edges
    edges = []
    edge_count = int(puzzle_config.get("edge_count", 0))
    for i in range(edge_count):
        start_key = f"edge_{i}_start"
        end_key = f"edge_{i}_end"
        if start_key in puzzle_config and end_key in puzzle_config:
            edges.append({
                "edge_index": i,
                "start_node": int(puzzle_config[start_key]),
                "end_node": int(puzzle_config[end_key])
            })

    # Build paths



    puzzle_data = schemas.PuzzleCreate(
        name=puzzle_config["name"],
        model=puzzle_config["model"],
        enemy_count=int(puzzle_config["enemy_count"]),
        player_unit_count=int(puzzle_config["player_unit_count"]),
        game_mode=puzzle_config["game_mode"],
        node_count=int(puzzle_config["node_count"]),
        edge_count=int(puzzle_config["edge_count"]),
        coins=int(puzzle_config["coins"]),
        turns=int(puzzle_config["turns"]),
        units=units, # adds list of units
        nodes=nodes, # add list of nodes
        edges=edges
    )

    # save using your service
    services = PuzzleServices(db)
    puzzle = services.create_puzzle(puzzle_data)
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


# API Delete Request - currently not in use
@router.delete("/{puzzle_id}", status_code=200)
async def delete_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Delete a puzzle"""
    services = PuzzleServices(db)
    services.delete_puzzle(puzzle_id)
    return {"detail": f"Puzzle {puzzle_id} deleted"}
