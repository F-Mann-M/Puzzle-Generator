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
from app.services import PuzzleServices
import plotly.graph_objects as go


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

    print("Form Content: ", puzzle_config) # for debugging

    units = []

    # Get Enemy Units
    enemy_count = int(puzzle_config.get("enemy_count", 0))
    for i in range(enemy_count):
        unit_type = puzzle_config.get(f"unit_enemy_{i}_type")

        path_nodes = []
        j = 0
        while f"unit_enemy_{i}_path_{j}" in puzzle_config:
            value = puzzle_config.get(f"unit_enemy_{i}_path_{j}")
            if value not in (None, ""):
                path_nodes.append(value)
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
            value = puzzle_config.get(f"unit_player_{i}_path_{j}")
            if value not in (None, ""):
                path_nodes.append(int(value))
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
            "x_position": (int(puzzle_config.get(f"node_{i}_x"))),
            "y_position": (int(puzzle_config.get(f"node_{i}_y")))
        }
        for i in range(node_count)
    ]

    # Get Edges
    edge_count = int(puzzle_config.get("edge_count", 0))
    edges = [
        {
            "edge_index": i,
            "start_node": (int(puzzle_config.get(f"edge_{i}_start"))),
            "end_node": (int(puzzle_config.get(f"edge_{i}_end")))
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
        model="Created by user",
        enemy_count=int(puzzle_config["enemy_count"]),
        player_unit_count=int(puzzle_config["player_unit_count"]),
        game_mode=puzzle_config["game_mode"],
        node_count=int(puzzle_config["node_count"]),
        edge_count=int(puzzle_config["edge_count"]),
        coins=int(puzzle_config["coins"]),
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
    print("Edge data: ", [edge.edge_index for edge in edge_data])
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
@router.get("/generate", response_class=HTMLResponse)
async def show_generate_puzzle(request: Request):
     return templates.TemplateResponse("generate-puzzle.html", {"request": request})


# Generate puzzle (LLM Endpoint)
@router.post("/generate")
async def generate_puzzle(request: Request, db: Session = Depends(get_db)):
    form_content = await request.form()
    puzzle_config = dict(form_content)

    print("Generate Puzzle From Content: ", puzzle_config) # debugging

    # get all units
    units = []

    # enemy units
    enemy_count = int(puzzle_config.get("enemy_count", 0))
    for i in range(enemy_count):
        unit_type = puzzle_config.get(f"enemy_type_{i}")
        movement = puzzle_config.get(f"enemy_movement_{i}")
        units.append({"faction": "enemy", "unit_type": unit_type, "movement": movement})

    # play units
    player_count = int(puzzle_config.get("player_unit_count", 0))
    for i in range(player_count):
        unit_type = puzzle_config.get(f"player_type_{i}")
        units.append({"faction": "player", "unit_type": unit_type})


    puzzle_config = schemas.PuzzleGenerate(
        model=puzzle_config.get("model"),
        game_mode=puzzle_config.get("game_mode"),
        node_count=puzzle_config.get("node_count"),
        edge_count=puzzle_config.get("edge_count"),
        turns=int(puzzle_config.get("turns")),
        units=units,
    )
    print("PuzzleGenerate object: ", puzzle_config) # Debugging


    services = PuzzleServices(db)
    generated_puzzle = await services.generate_puzzle(puzzle_config)

    print("Generated Puzzle: ", generated_puzzle)


    # get generated units, nodes, edges and paths from generated_puzzle
    # units = []
    # nodes = []
    # edges = []
    # path = []

    # puzzle = CreatePuzzle()
    # puzzle_id = services.create_puzzle(puzzle)
    # node_data = CreateNode()
    # node_map = services.create_nodes(node_data)
    # edge_data = CreateEdge()
    # services.create_edges(edge_data)
    # unit_data = CreateUnit()
    # services.create_units_with_path(puzzle_id, unit_data)
    # services.commit_all()
    # commit_all

    #return RedirectResponse(url=f"/puzzles/{puzzle_id}", status_code=303)


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


# Get puzzle by id
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

