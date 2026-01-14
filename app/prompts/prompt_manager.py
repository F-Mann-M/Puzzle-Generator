from app.prompts.prompt_game_rules import BASIC_RULES, GAME_MODE_SKIRMISH, GAME_MODE_SAFE_TRAVEL
import json
from typing import Optional
import logging
from utils.logger_config import configure_logging


async def get_puzzle_generation_prompt(
        db,
        example_puzzles,
        game_mode: str,
        node_count: int,
        edge_count: Optional[int],
        turns: int,
        units: list,
        description: Optional[int] = "",
        ) -> dict:

    
    # define game mode
    game_mode_prompt = ""
    if game_mode.lower() == "skirmish":
        game_mode_prompt = GAME_MODE_SKIRMISH
    elif game_mode.lower() == "safe_travel":
        game_mode_prompt = GAME_MODE_SAFE_TRAVEL

    prompt = {"system_prompt": (
        f"""
        You are a game designer who creates puzzles based on these {BASIC_RULES} and this {game_mode_prompt}.
        You will create all nodes, edges, and paths for enemy units and player units.
        Since the paths of the player units are also the solution of each puzzle, you must provide the puzzle with the solution (how to place and move player units).
        Mind further instruction in {description}
        
        The generator must always output valid JSON matching the PuzzleLLMResponse schema exactly.
        
        ### JSON Schema Definitions (TypeScript)
        
        interface PuzzleLLMResponse {{
          nodes: NodeGenerate[];
          edges: EdgeGenerate[];
          units: UnitGenerate[];
          coins: number;
          description: string; // Describe moves in detail turn by turn. Use \\n for new paragraphs.
        }}
        
        interface NodeGenerate {{
          index: number;
          x: number;
          y: number;
        }}
        
        interface EdgeGenerate {{
          index: number; // Must be an integer
          start: number; // Index of the start node
          end: number;   // Index of the end node
          // STRICTLY FORBIDDEN: Do NOT include 'x' or 'y' in edges.
        }}
        
        interface UnitGenerate {{
          type: string;
          faction: string;
          path: number[]; // List of node indices
        }}
        
        ### Constraints
        1. Return ONLY a valid JSON object conforming to the schema above.
        2. Return no explanations, only raw JSON.
        3. For Edges: strictly use keys 'index', 'start', 'end'. 
        4. Do NOT use aliases like 'from', 'to', 'source', 'target'.
        5. Do NOT include coordinates (x, y) in Edges.
        6. Ensure each list is a JSON array ([...]), not an object with keys.
        
        These are example puzzles in JSON format: {json.dumps(example_puzzles, indent=2)}
        Use these examples as reference for structure, difficulty, and puzzle design patterns.
        """
        ),
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
        if {edge_count} does not provide values, generate edges
        Number of Units: {len(units)}
        
        Units:
        {json.dumps(units, indent=2)}
        
        Return ONLY valid JSON for PuzzleLLMResponse.
        """)
    }
    print(f"Prompt built successfully (nodes={node_count}, edges={edge_count}, units={len(units)}")
    return prompt

