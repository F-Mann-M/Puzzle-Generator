from fastapi import HTTPException
import json
from app.prompts.prompt_game_rules import BASIC_RULES
from app.schemas import PuzzleGenerate, PuzzleCreate, NodeCreate, EdgeCreate, UnitCreate, PuzzleExport
from app.services import PuzzleServices
from app.llm.llm_manager import get_llm
from uuid import UUID
from typing import Any


class AgentTools:

    def __init__(self, db):
        self.db = db

    async def generate_puzzle(self, puzzle_config: PuzzleGenerate) -> UUID:
        """ Generate a new puzzle"""
        services = PuzzleServices(self.db)
        puzzle_generated = await services.generate_puzzle(puzzle_config)
        new_puzzle = services.create_puzzle(puzzle_generated)
        return new_puzzle.id

    async def update_puzzle(self, puzzle_id: UUID, message: str, model: str) -> dict[str, Any]:
        """ Update an existing puzzle"""
        TOOL = "update_puzzle: "
        print(f"\n{TOOL} Takes in current puzzle data and message: ", message)
        puzzle_services = PuzzleServices(self.db)

        # Get puzzle data
        print(f"{TOOL} Get puzzle by ID")
        try:
            puzzle = puzzle_services.get_puzzle_by_id(puzzle_id)
        except Exception as e:
            print(f"{TOOL} Error fetching puzzle: {e}")
            return {f"tool_result": [f"{TOOL} Error fetching puzzle: {e}"]}

        # # validate and convert puzzle data to hand it over to LLM
        # print(f"{TOOL} validate and convert puzzle object")
        # print(f"DEBUG: PuzzleCreate config: {PuzzleCreate.model_config}")
        # print(f"DEBUG: NodeCreate config: {NodeCreate.model_config}")
        # print(f"DEBUG: NodeCreate config: {UnitCreate.model_config}")
        # print(f"DEBUG: NodeCreate config: {EdgeCreate.model_config}")
        # print(f"DEBUG: NodeCreate config: {PuzzleExport.model_config}")
        # try:
        #     current_puzzle = PuzzleExport.model_validate(puzzle, from_attributes=True)
        # except Exception as e:
        #     print(f"{TOOL} Error validating puzzle: {e}")

        print(f"{TOOL} serialise puzzle manually...")
        current_puzzle = {
            "name": puzzle.name,
            "model": model,
            "game_mode": puzzle.game_mode,
            "coins": puzzle.coins,
            "nodes": [
                {
                    "id": str(node.id),
                    "node_index": node.node_index,
                    "x_position": node.x_position,
                    "y_position": node.y_position,
                    "puzzle_id": str(puzzle_id)
                }
                for node in sorted(puzzle.nodes, key=lambda n: n.node_index)
            ],
            "edges": [
                {
                    "edge_index": edge.edge_index,
                    "start_node_id": str(edge.start_node_id),
                    "end_node_id": str(edge.end_node_id),
                    "puzzle_id": str(puzzle_id)
                }
                for edge in sorted(puzzle.edges, key=lambda e: e.edge_index)
            ],
            "units": [
                {
                    "id": str(unit.id),
                    "unit_type": unit.unit_type,
                    "faction": unit.faction,
                    "puzzle_id": str(puzzle_id),
                    "path": {
                        "path_node": [
                            {
                                "node_id": str(path_node.node_id),
                                "order_index": path_node.order_index,
                                "node_index": path_node.node_index
                            }
                            for path_node in sorted(unit.path.path_node, key=lambda pn: pn.order_index)
                        ]
                    } if unit.path and unit.path.path_node else {"path_node": []}
                }
                for unit in puzzle.units
            ],
            "description": puzzle.description,
        }
        print(f"{TOOL} puzzle serialised: \n{current_puzzle}")

        # convert puzzle in to JSON
        try:
            current_puzzle_json = json.dumps(current_puzzle)
            print(f"{TOOL} convert to JSON \n {current_puzzle_json}")
        except Exception as e:
            print(f"{TOOL} Error converting puzzle: {e}")

        # update existing puzzle
        llm = get_llm(model)
        system_prompt = f"""
        You are an assistant who extracts puzzle modification parameters from this message.
        and modify this existing puzzle data {current_puzzle_json}.
        Use the existing puzzle data to understand what kind of data have do added, deleted, changed or modified.
        This are the rules {BASIC_RULES} for the puzzle. 
        Mind this rules while adding modifications to the existing puzzle data.
        Return ONLY a valid JSON object conforming to this Pydantic schema: {PuzzleCreate}
        """
        prompt = {"system_prompt": system_prompt, "user_prompt": message}

        print(f"{TOOL} Extracting data from user message and modifying existing puzzle data...")
        try:
            updated_puzzle_data = await llm.structured(prompt=prompt, schema=PuzzleCreate)
            if not updated_puzzle_data:
                print(f"{TOOL} Failed to generate modified puzzle data")
                raise Exception("Failed to generate modified puzzle data")

            print(f"{TOOL} Updating current puzzle data...")
            puzzle_updated = puzzle_services.update_puzzle(puzzle_id, updated_puzzle_data)
            if not puzzle_updated:
                raise Exception("update_puzzle: Failed to update existing puzzle data: ")
            print(f"{TOOL} Successfully updated puzzle data")

        except Exception as e:
            print(f"{TOOL} Failed to update puzzle data: {e}")
            return {"tool_result": [f"{TOOL}: Error: {e}"]}

        # generate tool result message
        puzzle_serialized = puzzle_services.serialize_puzzle(puzzle_id)
        puzzle_updated_json = json.dumps(puzzle_serialized)
        print(f"{TOOL}: Updated puzzle successfully!")

        print(f"{TOOL} Generating tool response...")
        try:
            system_prompt_summary = f"""
            You are an assistant who compares this old puzzle data {current_puzzle_json}
            with modified puzzle data. Use this {BASIC_RULES} to understand and summerize changes.
            """
            summary_prompt = {"system_prompt": system_prompt_summary, "user_prompt": puzzle_updated_json}
            tool_summary = await llm.chat(summary_prompt)
            if not tool_summary:
                raise Exception(f"{TOOL} Failed to generate summary data: ")

            print(f"{TOOL} Generated tool response: \n", tool_summary)
            return {"tool_result": [f"{TOOL}: Updated puzzle successfully! {tool_summary}"]}

        except Exception as e:
            print(f"{TOOL} Failed to generate tool response: {e}")
            return {"tool_result": [f"{TOOL}: Error: {e}"]}

    def validate_puzzle(self):
        """ Validate an existing puzzle"""
        pass

    def delete_puzzle(self):
        """ Delete an existing puzzle"""
        pass

# get tools description
# generate puzzle
# modify puzzle
# validate puzzle
# get puzzle rules
# visualize puzzle
# update puzzle
# list puzzle
# delete puzzle
