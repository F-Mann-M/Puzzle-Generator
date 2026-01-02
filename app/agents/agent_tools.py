from fastapi import HTTPException
import json
from app.prompts.prompt_game_rules import BASIC_RULES
from app.schemas import PuzzleGenerate, PuzzleCreate
from app.services import PuzzleServices
from app.llm.llm_manager import get_llm
from uuid import UUID
from typing import Any
from app.agents.

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
        print("\nupdate_puzzle: Takes in current puzzle data and message: ", message)
        TOOL = "update_puzzle: "
        tool_response = []
        puzzle_services = PuzzleServices(self.db)

        # Get puzzle meta data
        print("update_puzzle: Get puzzle by ID")
        try:
            puzzle = puzzle_services.get_puzzle_by_id(puzzle_id)
        except Exception as e:
            print("Error fetching puzzle: ", e)
            return {f"tool_result": f"{TOOL} Error fetching puzzle: {e}"}

        # validate and convert puzzle data to hand it over to LLM
        print("validate and convert puzzle object")
        current_puzzle = PuzzleCreate.model_validate(puzzle)
        if not current_puzzle:
            tool_response.append(f"{TOOL} Could not validate puzzle")
            return {f"tool_result": tool_response}

        # convert puzzle in to JSON
        current_puzzle_json = json.dumps(current_puzzle)
        print("update_puzzle: convert to JSON \n", current_puzzle_json)

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

        print("update_puzzle: Extracting data from user message and modifying existing puzzle data...")
        try:
            updated_puzzle_data = await llm.structured(prompt=prompt, schema_class=PuzzleCreate)
            if not updated_puzzle_data:
                raise Exception("Failed to modify puzzle data: ")

            print("update_puzzle: Updating current puzzle data...")
            puzzle_updated = puzzle_services.update_puzzle(puzzle_id, updated_puzzle_data)
            if not puzzle_updated:
                raise Exception("update_puzzle: Failed to update existing puzzle data: ")
            print("update_puzzle: Successfully updated puzzle data")

        except Exception as e:
            print(f"update_puzzle: Failed to update puzzle data: {e}")
            tool_response.append(f"{TOOL}: Error: {e}")
            print("update_puzzle: tool_response: ", tool_response)
            return {"tool_result": tool_response}

        # generate tool result message
        puzzle_serialized = puzzle_services.serialize_puzzle(puzzle_id)
        puzzle_updated_json = json.dumps(puzzle_serialized)
        tool_response.append(f"{TOOL}: Updated puzzle successfully!")

        print("update_puzzle: Generating tool response...")
        try:
            system_prompt_summary = f"""
            You are an assistant who compares this old puzzle data {current_puzzle_json}
            with modified puzzle data. Use this {BASIC_RULES} to understand and summerize changes.
            """
            summary_prompt = {"system_prompt": system_prompt_summary, "user_prompt": puzzle_updated_json}
            tool_summary = await llm.modify(summary_prompt)
            if not tool_summary:
                raise Exception("Failed to generate summary data: ")

            print("update_puzzle: Generated tool response: \n", tool_summary)

            tool_response.append(f"{TOOL}: {tool_summary}")
            return {"tool_result": tool_response}

        except Exception as e:
            print(f"update_puzzle: Failed to generate tool response: {e}")
            tool_response.append(f"{TOOL}: Error: {e}")
            return {"tool_result": tool_response}


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


