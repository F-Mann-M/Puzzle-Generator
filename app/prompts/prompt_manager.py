BASIC_RULES = """
A puzzle is based on nodes and edges placed on a 10x10 grid.
- Nodes follow the Node schema: each node has integer x, y coordinates and an index (starting from 0).
- Edges connect two nodes via their indexes and also include x and y coordinates.
- Units follow the Unit schema: each unit has a faction, unit_type, and a path (list of node indexes).
- Only one unit can occupy a node.
- The top-level object must follow the PuzzleLLMResponse schema strictly.
"""



async def get_prompt(game_mode: str, node_count: int, edge_count: int, turns: int, units: list) -> list:
    print("Edge Count: ", edge_count)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a JSON generator for a puzzle system. "
                "Return ONLY a valid JSON object conforming to this Pydantic schema: "
                "PuzzleLLMResponse { nodes: List[NodeGenerate], edges: List[EdgeGenerate], "
                "units: List[UnitGenerate], coins: int }. "
                "Ensure each list is a JSON array ([...]) not an object with numeric keys. "
                "Return no explanations, only raw JSON."
                "For the EdgeGenerate schema ONLY use *only* these key names: 'index', 'start', 'end', 'x', 'y'."
                "Do NOT use aliases like 'from', 'to', 'from_index', 'to_index'."
                "Each edge’s 'start' and 'end' must correspond to existing node indexes"
                "For the UnitGenerate schema ONLY use *only* these key names: 'unit_type', 'faction', 'path'"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Generate a puzzle following these rules:\n{BASIC_RULES}\n\n"
                f"The puzzle has {node_count} nodes and {edge_count} edges. "
                f"Place these units on nodes: {units}. "
                f"The game mode is '{game_mode}' and the number of turns is {turns}. "
                "The 'coins' field must be an integer (e.g. 5). "
                "Edges must connect existing node indexes (0–N). "
                "Return each list as a JSON array, not an object."
                "Follow all schema rules strictly"
            ),
        },
    ]

    print(f"Prompt built successfully (nodes={node_count}, edges={edge_count}, units={len(units)})")
    return messages