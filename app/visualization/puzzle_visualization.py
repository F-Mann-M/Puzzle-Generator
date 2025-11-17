import plotly.graph_objects as go
import random
import itertools


def generate_puzzle_visualization(puzzle):
    """Generate a Plotly figure from a puzzle ORM object."""
    positions = {n.id: (n.x_position, n.y_position) for n in puzzle.nodes}
    edge_x, edge_y = [], []
    for e in puzzle.edges:
        x0, y0 = positions[e.start_node_id]
        x1, y1 = positions[e.end_node_id]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", line=dict(width=4, color="#aaa"), name="Edges"
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
        marker=dict(size=40, color="white", line=dict(width=4, color="black")),
        name="Nodes"
    ))

    fig.update_layout(
        title=f"Puzzle: {getattr(puzzle, 'name', 'Preview')}",
        showlegend=True,
        plot_bgcolor="white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=600
    )

    return fig


def generate_preview_visualization(config: dict):
    import plotly.graph_objects as go
    import random, itertools

    def safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    # ✅ Only use these
    node_count = safe_int(config.get("node_count"))
    edge_count = safe_int(config.get("edge_count"))

    # ignore everything else (coins, units, etc.)
    if node_count <= 0:
        return go.Figure()

    # optional: stable randomization
    random.seed(42)

    # --- Generate nodes ---
    nodes = [
        {"index": i, "x": random.randint(0, 10), "y": random.randint(0, 10)}
        for i in range(node_count)
    ]

    # --- Generate edges ---
    possible_edges = list(itertools.combinations(range(node_count), 2))
    random.shuffle(possible_edges)
    edges = [
        {"start": a, "end": b}
        for (a, b) in possible_edges[:edge_count]
    ]

    # --- Create figure ---
    fig = go.Figure()

    # Draw edges
    for e in edges:
        start = nodes[e["start"]]
        end = nodes[e["end"]]
        fig.add_trace(go.Scatter(
            x=[start["x"], end["x"]],
            y=[start["y"], end["y"]],
            mode="lines",
            line=dict(color="#aaa", width=3),
            hoverinfo="none"
        ))

    # Draw nodes
    fig.add_trace(go.Scatter(
        x=[n["x"] for n in nodes],
        y=[n["y"] for n in nodes],
        mode="markers+text",
        text=[n["index"] for n in nodes],
        textposition="middle center",
        marker=dict(size=14, color="skyblue", line=dict(width=2, color="black")),
        hoverinfo="text"
    ))

    fig.update_layout(
        title="Puzzle Preview",
        plot_bgcolor="white",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=500
    )

    return fig


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default