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

# Create puzzle by you own
@router.post("/", response_class=HTMLResponse)
async def create_puzzle(request: Request, db: Session = Depends(get_db)):
    # get data from form and store in dict
    services = PuzzleServices(db)
    form_content = await request.form()
    puzzle_config = dict(form_content)

    print("From Content: ", puzzle_config) # for debugging

    units = []

    # Get Enemy Units
    enemy_count = int(puzzle_config.get("enemy_count", 0))
    for i in range(enemy_count):
        unit_type = puzzle_config.get(f"unit_enemy_{i}_type")

        path_nodes = []
        j = 0
        while f"unit_enemy_{i}_path_{j}" in puzzle_config:
            path_nodes.append(int(puzzle_config.get(f"unit_enemy_{i}_path_{j}"))-1)
            j += 1

        units.append(
            {
                "faction": "enemy",
                "unit_type": unit_type,
                "path_nodes": path_nodes
            }
        )

    # Player Units
    player_count = int(puzzle_config.get("player_unit_count", 0))
    for i in range(player_count):
        unit_type = puzzle_config.get(f"unit_player_{i}_type")

        path_nodes = []
        j = 0
        while f"unit_player_{i}_path_{j}" in puzzle_config:
            path_nodes.append((int(puzzle_config.get(f"unit_player_{i}_path_{j}"))-1))
            j += 1

        units.append(
            {
                "faction": "player",
                "unit_type": unit_type,
                "path_nodes": path_nodes
            }
        )

    # Get Nodes
    node_count = int(puzzle_config.get("node_count", 0))
    nodes = [
        {
            "node_index": i,
            "x_position": (int(puzzle_config.get(f"node_{i + 1}_x"))),
            "y_position": (int(puzzle_config.get(f"node_{i + 1}_y")))
        }
        for i in range(node_count)
    ]

    # Get Edges
    edge_count = int(puzzle_config.get("edge_count", 0))
    edges = [
        {
            "edge_index": i,
            "start_node": (int(puzzle_config.get(f"edge_{i + 1}_start")))-1,
            "end_node": (int(puzzle_config.get(f"edge_{i + 1}_end")))-1
        }
        for i in range(edge_count)
    ]

    #### for debugging ###
    print("units: ", units)
    print("nodes: ", nodes)
    print("Eges: ", edges)

    # Create Puzzle
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
    )
    puzzle_id = services.create_puzzle(puzzle_data)

    # Create Nodes
    node_data = []
    for node in nodes:
       node_data.append(
           schemas.NodeCreate(
               node_index=node.get("node_index"),
               x_position=node.get("x_position"),
               y_position=node.get("y_position"),
               puzzle_id=puzzle_id
            )
       )
    node_map = services.create_nodes(node_data)


    # Create Edges
    edge_data = []
    for edge in edges:
        start_uuid = node_map.get(edge.get("start_node"))
        end_uuid = node_map.get(edge.get("end_node"))
        edge_data.append(
            schemas.EdgeCreate(
                edge_index=edge.get("edge_index"),
                start_node_id=start_uuid,
                end_node_id=end_uuid,
                puzzle_id=puzzle_id
            )
        )
    services.create_edges(edge_data)

    # for debugging
    print("units dict path nodes: ", [unit.get("path_nodes") for unit in units])

    # Create Units with path
    unit_data = []
    for unit in units:
        unit_data.append(
            schemas.UnitCreate(
                faction=unit.get("faction"),
                unit_type=unit.get("unit_type"),
                path_nodes=unit.get("path_nodes"),
                puzzle_id=puzzle_id
        ))

    services.create_units_with_path(puzzle_id, unit_data)

    # Commit all
    services.commit_all()

    return RedirectResponse(url=f"/puzzles/{puzzle_id}", status_code=303)


# load puzzle generator
@router.get("/generate-puzzle", response_class=HTMLResponse)
async def show_generate_puzzle(request: Request):
    return templates.TemplateResponse("generate-puzzle.html", {"request": request})

# Generate puzzle (LLM Endpoint)
@router.post("/generate-puzzle", response_class=HTMLResponse)
async def generate_puzzle(request: Request):
    form_content = await request.form()
    puzzle_config = dict(form_content)

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


# API Delete Request
@router.delete("/{puzzle_id}", status_code=200)
async def delete_puzzle(puzzle_id: UUID, db: Session = Depends(get_db)):
    """Delete a puzzle"""
    services = PuzzleServices(db)
    services.delete_puzzle(puzzle_id)
    return {"detail": f"Puzzle {puzzle_id} deleted"}

