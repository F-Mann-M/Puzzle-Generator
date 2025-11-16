from app.prompts.prompt_game_rules import BASIC_RULES, GAME_MODE_SKIRMISH, GAME_MODE_SAFE_TRAVEL
import json


async def get_prompt(game_mode: str, node_count: int, edge_count: int, turns: int, units: list) -> dict:
    print("\n****** Values for prompt generation *****")
    print("Edge Count: ", edge_count)
    print("Node Count: ", node_count)
    print("Turns: ", turns)
    print("Gamer Mode: ", game_mode)

    # define game mode
    if game_mode.lower() == "skirmish":
        game_mode_prompt = GAME_MODE_SKIRMISH
    elif game_mode.lower() == "safe_travel":
        game_mode_prompt = GAME_MODE_SAFE_TRAVEL

    prompt = {"system_prompt": (
        f"You are a game designer how creates puzzles based on this {BASIC_RULES} and this {game_mode_prompt}"
        "You will create all nodes, edges and paths for enemy units and player units."
        "Since the path of the player units are also the solution of each puzzle you provide the puzzle with the solution (how to place and to move player units)"
        "You provide complete puzzles with solutions"
        "You are a JSON generator for a puzzle system. "
        "Return ONLY a valid JSON object conforming to this Pydantic schema: "
        "PuzzleLLMResponse { nodes: List[NodeGenerate], edges: List[EdgeGenerate], "
        "units: List[UnitGenerate], coins: int }. "
        "Ensure each list is a JSON array ([...]) not an object with numeric keys. "
        "Return no explanations, only raw JSON."
        "For the EdgeGenerate schema ONLY use *only* these key names: 'index', 'start', 'end', 'x', 'y'."
        "Do NOT use aliases like 'from', 'to', 'from_index', 'to_index'."
        "Each edge’s 'start' and 'end' must correspond to existing node indexes"
        "For the UnitGenerate schema ONLY use *only* these key names: 'type', 'faction', 'path'"),
    "user_prompt": (f"""
        # User Prompt: Generate Puzzle Scenario
        
        You are to create a new puzzle following all the rules and schema definitions provided in the system prompt.
        Make sure the puzzle works. It outcome have to follow {BASIC_RULES} and the {game_mode_prompt}.
        Make sure there are coins. the number of coins depends on the number of turns and extra costs for mobs
        
        Generate a puzzle that satisfies the following parameters:
        
        Game Mode: {game_mode}
        Turns: {turns} 
        Number of Nodes: {node_count}
        Number of Edges: {edge_count}
        Number of Units: {len(units)}
        
        Units:
        {json.dumps(units, indent=2)}
        
        Return only valid JSON for PuzzleLLMResponse.
        """)

    }
    print(f"Prompt built successfully (nodes={node_count}, edges={edge_count}, units={len(units)}")
    return prompt
