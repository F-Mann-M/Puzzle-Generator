# import moduls/libraries

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from pathlib import Path

# import form project
from app.core.database import get_db
from app import schemas
from app import models
from app.schemas import PuzzleCreate, PuzzleGenerate
from app.services import PuzzleServices
import plotly.graph_objects as go
import json


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
    """
    Create a new puzzle using JSON data sent by the frontend.

    Expected JSON structure:
    {
      "name": "My Puzzle",
      "model": "Created by user",
      "game_mode": "Skirmish",
      "coins": 10,
      "nodes": [
        {"index": 0, "x_position": 1, "y_position": 2},
        {"index": 1, "x_position": 3, "y_position": 4}
      ],
      "edges": [
        {"start": 0, "end": 1}
      ],
      "units": [
        {"faction": "enemy", "type": "Grunt", "path": [0,1,2]}
        {"faction": "player", "type": "Swordsman", "path": [2,1]}
      ]
    }
    """

    services = PuzzleServices(db)
    new_puzzle = services.create_puzzle(puzzle)
    return RedirectResponse(url=f"/puzzles/{new_puzzle.id}", status_code=303)

# Load puzzle generator
@router.get("/generate", response_class=HTMLResponse)
async def show_generate_puzzle(request: Request):
     return templates.TemplateResponse("generate-puzzle.html", {"request": request})


# Generate puzzle (LLM Endpoint)
@router.post("/generate")
async def generate_puzzle(request: Request, puzzle_generate: PuzzleGenerate, db: Session = Depends(get_db)):
    services = PuzzleServices(db)
    #
    new_puzzle = services.create_puzzle(puzzle)
    return RedirectResponse(url=f"/puzzles/{new_puzzle.id}", status_code=303)
    # form_content = await request.form()
    # puzzle_config = dict(form_content)
    #
    # print("Generate Puzzle From Content: ", puzzle_config) # debugging
    #
    # # get all units
    # units = []
    #
    # # enemy units
    # enemy_count = int(puzzle_config.get("enemy_count", 0))
    # for i in range(enemy_count):
    #     unit_type = puzzle_config.get(f"enemy_type_{i}")
    #     movement = puzzle_config.get(f"enemy_movement_{i}")
    #     units.append({"faction": "enemy", "unit_type": unit_type, "movement": movement})
    #
    # # play units
    # player_count = int(puzzle_config.get("player_unit_count", 0))
    # for i in range(player_count):
    #     unit_type = puzzle_config.get(f"player_type_{i}")
    #     units.append({"faction": "player", "unit_type": unit_type})
    #
    #
    # puzzle_setup= schemas.PuzzleGenerate(
    #     model=puzzle_config.get("model"),
    #     game_mode=puzzle_config.get("game_mode"),
    #     node_count=puzzle_config.get("node_count"),
    #     edge_count=puzzle_config.get("edge_count"),
    #     turns=int(puzzle_config.get("turns")),
    #     units=units,
    # )
    # print("PuzzleGenerate object: ", puzzle_setup) # Debugging
    #
    # # generate puzzle
    # services = PuzzleServices(db)
    # puzzle_generated = await services.generate_puzzle(puzzle_setup)
    #
    # # Debugging
    # print("Generated Puzzle: ", puzzle_generated)
    # print("Nodes: ", puzzle_generated.nodes)
    # print("Edges: ", puzzle_generated.edges)
    # print("Units: ", puzzle_generated.units)
    #
    # # Create Puzzle
    # puzzle = schemas.PuzzleCreate(
    #     name=puzzle_config.get("name"),
    #     model=puzzle_config.get("model"),
    #     enemy_count=int(puzzle_config.get("enemy_count")),
    #     player_unit_count=int(puzzle_config.get("player_unit_count")),
    #     game_mode=puzzle_config.get("game_mode"),
    #     node_count=int(puzzle_config.get("node_count")),
    #     edge_count=int(puzzle_config.get("edge_count")),
    #     coins=puzzle_generated.coins
    # )
    # puzzle_id = services.create_puzzle(puzzle)
    # print("\n\npuzzle id: ", puzzle_id)
    #
    #
    # # Create Nodes
    # node_data = []
    # for node in puzzle_generated.nodes:
    #     node_data.append(schemas.NodeCreate(
    #         node_index=node.index,
    #         x_position=node.x,
    #         y_position=node.y,
    #         puzzle_id=puzzle_id
    #     ))
    # print("\n\nNode Data: ", node_data)
    # node_map = services.create_nodes(node_data)
    # print("Node map: ", node_map)
    #
    #
    # # Create Edges
    # edge_data = []
    # for edge in puzzle_generated.edges:
    #     start_uuid = node_map.get(edge.start)
    #     end_uuid = node_map.get(edge.end)
    #     edge_data.append(
    #         schemas.EdgeCreate(
    #             edge_index=edge.index,
    #             start_node_id=start_uuid,
    #             end_node_id=end_uuid,
    #             puzzle_id=puzzle_id
    #         )
    #     )
    # services.create_edges(edge_data)
    #
    #
    # # debugging
    # print("Edge data: ", [edge.edge_index for edge in edge_data])
    #
    #
    # # Create Units with path
    # unit_data = []
    # for unit in puzzle_generated.units:
    #     unit_data.append(
    #         schemas.UnitCreate(
    #             faction=unit.faction,
    #             unit_type=unit.unit_type,
    #             path_nodes=unit.path,
    #             puzzle_id=puzzle_id
    #         ))
    # print("Path in unit_data: ", [unit.path_nodes for unit in unit_data])
    # services.create_units_with_path(puzzle_id, unit_data)
    #
    # # Commit all
    # services.commit_all()

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

