from fastapi import HTTPException
import json
from app.prompts.prompt_game_rules import BASIC_RULES
from app.schemas import PuzzleGenerate, PuzzleCreate
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
        print("Takes in current puzzle data")
        TOOL = "modify"
        tool_response = []
        # get puzzle data by puzzle id
        puzzle_services = PuzzleServices(self.db)
        puzzle = puzzle_services.get_puzzle_by_id(puzzle_id)
        if not puzzle:
            raise HTTPException(status_code=404, detail="Puzzle not found")

        # serialize puzzle data to hand it over to LLM
        print("Serialize current puzzle data")
        current_puzzle = await puzzle_services.serialize_puzzle(puzzle)

        # convert puzzle in to JSON
        current_puzzle_json = json.dumps(current_puzzle)

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

        print("Extracting data from user message and modifying existing puzzle data...")
        try:
            updated_puzzle_data = await llm.modify(prompt)
            if not updated_puzzle_data:
                raise Exception("Failed to modify puzzle data: ")

            print("Updating current puzzle data...")
            puzzle_updated = puzzle_services.update_puzzle(puzzle_id, updated_puzzle_data)
            if not puzzle_updated:
                raise Exception("Failed to update existing puzzle data: ")
            print("Successfully updated puzzle data")

        except Exception as e:
            print(f"Failed to update puzzle data: {e}")
            tool_response.append(f"{TOOL}: Error: {e}")
            return {"tool_result": TOOL + tool_response}

        # generate tool result message
        puzzle_serialized = puzzle_services.serialize_puzzle(puzzle_id)
        puzzle_updated_json = json.dumps(puzzle_serialized)
        tool_response.append(f"{TOOL}: Updated puzzle successfully!")

        print("Generating tool response...")
        try:
            system_prompt_summary = f"""
            You are an assistant who compares this old puzzle data {current_puzzle_json}
            with modified puzzle data. Use this {BASIC_RULES} to understand and summerize changes.
            """
            summary_prompt = {"system_prompt": system_prompt_summary, "user_prompt": puzzle_updated_json}
            tool_summary = await llm.modify(summary_prompt)
            if not tool_summary:
                raise Exception("Failed to modify summary data: ")

            print("Generated tool response: \n", tool_summary)

            tool_response.append(f"{TOOL}: {tool_summary}")
            return {"tool_result": tool_response}

        except Exception as e:
            print(f"Failed to generate tool response: {e}")
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

# check if chat generate a puzzle

