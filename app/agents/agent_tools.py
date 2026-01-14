import json
from deepdiff import DeepDiff
from app.prompts.prompt_game_rules import BASIC_RULES
from app.schemas import PuzzleGenerate, PuzzleCreate
from app.services import PuzzleServices
from app.llm.llm_manager import get_llm
from uuid import UUID
from typing import Any, Union
from app.models import Puzzle
import logging
from utils.logger_config import configure_logging
logger = logging.getLogger(__name__)


class AgentTools:

    def __init__(self, db):
        self.db = db

    async def generate_puzzle(self, puzzle_config: PuzzleGenerate) -> UUID:
        """ Generate a new puzzle"""
        services = PuzzleServices(self.db)
        puzzle_generated = await services.generate_puzzle(puzzle_config)

        if puzzle_generated is None:
            raise Exception("agent_tool.generate_puzzle: Failed to generate puzzle data from LLM.")

        new_puzzle = services.create_puzzle(puzzle_generated)
        return new_puzzle.id


    async def _get_node_index(self, node_id, puzzle) -> Union[int, dict]:
        """Take in node ID and Puzzle Object and return index of node with node_id"""

        TOOL = "agent_tools.generate_puzzle:"
        logger.debug(f"Start/End node ID: {node_id}")
        for node in puzzle.nodes:
            if str(node.id) == str(node_id):
                logger.debug(f"{TOOL} Node ID: {node.id} matches with node ID: {node_id}")
                return node.node_index
        logger.warning(f"{TOOL} No index found for node {node_id}")
        return {"tool_result": "can not find index"}


    async def serialize_puzzle_obj_for_llm(self, puzzle: Puzzle, model) -> json:
        """Serialize a Puzzle object to LLM readable json"""
        TOOL = "agent_tools.serialize_puzzle_obj_for_llm:"

        current_puzzle = Puzzle
        logger.debug(f"{TOOL} serialise puzzle...")
        try:
            current_puzzle = {
                "name": puzzle.name,
                "model": model,
                "game_mode": puzzle.game_mode,
                "coins": puzzle.coins,
                "nodes": [
                    {
                        "index": node.node_index,
                        "x": node.x_position,
                        "y": node.y_position,
                    }
                    for node in sorted(puzzle.nodes, key=lambda n: n.node_index)
                ],
                "edges": [
                    {
                        "index": edge.edge_index,
                        # go through node UUIDs of the current puzzle and compare with start_node_id/ end_node_id
                        # to get the index of the node
                        "start": await self._get_node_index(str(edge.start_node_id), puzzle),
                        "end": await self._get_node_index(str(edge.end_node_id), puzzle),
                    }
                    for edge in sorted(puzzle.edges, key=lambda e: e.edge_index)
                ],
                "units": [
                    {
                        "type": unit.unit_type,
                        "faction": unit.faction,
                        "path": (
                            [
                                # get node index for nodes of the path
                                # and sort them to keep it in the right order
                                path_node.node_index for path_node in
                                sorted(unit.path.path_node, key=lambda pn: pn.order_index)
                            ]),
                    }
                    for unit in puzzle.units
                ],
                "description": puzzle.description,
            }
            #print(f"{TOOL} puzzle serialised")

        except Exception as e:
            logger.error(f"{TOOL} Error serialising puzzle: {e}")


        # convert puzzle in to JSON
        try:
            logger.info(f"{TOOL} convert to JSON...")
            current_puzzle_json = json.dumps(current_puzzle)
            return current_puzzle_json

        except Exception as e:
            logger.error(f"{TOOL} Error converting puzzle: {e}")


    async def extract_puzzle_diff(self, puzzle_a: dict, puzzle_b: dict) -> list:
        """Extract differences from puzzle a to puzzle b"""

        # Compare
        diff = DeepDiff(puzzle_a, puzzle_b, ignore_order=True)

        # Convert to a flat list of messages
        diff_list = []

        # value_changed is for keys that exist in both but have different values
        if 'values_changed' in diff:
            for path, change in diff['values_changed'].items():
                diff_list.append(f"Updated {path}: {change['old_value']} -> {change['new_value']}")

        # dictionary_item_added is for new keys
        if 'dictionary_item_added' in diff:
            for path in diff['dictionary_item_added']:
                diff_list.append(f"Added field: {path}")

        # iterable_item_added is for new items in lists
        if 'iterable_item_added' in diff:
            for path in diff['iterable_item_added']:
                 diff_list.append(f"Added to list: {path}")

        return diff_list


    async def update_puzzle(
            self,
            puzzle_id: Union[UUID, str],
            message: str,
            model: str,
            session_id: Union[UUID, str]) -> dict[str, Any]:
        """ Update an existing puzzle"""
        TOOL = "ChatAgent.update_puzzle: "
        logger.info(f"{TOOL} Takes in current puzzle data and message: {message}")

        # Ensure puzzle_id is a UUID object, not a string
        puzzle_id = self.ensure_uuid(puzzle_id)

        # Get puzzle data
        puzzle_services = PuzzleServices(self.db)
        logger.debug(f"{TOOL} Get puzzle by ID")
        try:
            # get puzzle by id
            puzzle = puzzle_services.get_puzzle_by_id(puzzle_id)
        except Exception as e:
            logger.error(f"{TOOL} Error fetching puzzle: {e}")
            return {f"tool_result": [f"{TOOL} Error fetching puzzle: {e}"]}

        # Serialise puzzle data
        puzzle_json = await self.serialize_puzzle_obj_for_llm(puzzle, model)

        # update existing puzzle
        llm = get_llm(model)
        system_prompt = f"""
        You are an assistant who extracts puzzle modification parameters from this message.
        and modify this existing puzzle data {puzzle_json}.
        Use the existing puzzle data to understand what kind of data have do added, deleted, changed or modified.
        This are the rules {BASIC_RULES} for the puzzle. 
        Mind this rules while adding modifications to the existing puzzle data.
        Return ONLY a valid JSON object conforming to this Pydantic schema: {PuzzleCreate}
        """
        prompt = {"system_prompt": system_prompt, "user_prompt": message}

        logger.info(f"{TOOL} Extracting data from user message and modifying existing puzzle data...")
        try:
            updated_puzzle_data = await llm.structured(prompt=prompt, schema=PuzzleCreate)
            if not updated_puzzle_data:
                logger.error(f"{TOOL} Failed to generate modified puzzle data")
                raise Exception("Failed to generate modified puzzle data")

            logger.info(f"{TOOL} Updating current puzzle data...")
            puzzle_updated = puzzle_services.update_puzzle(
                puzzle_id=puzzle_id,
                puzzle_data=updated_puzzle_data)
            if not puzzle_updated:
                raise Exception(f"{TOOL} Failed to update existing puzzle data.")

            logger.info(f"{TOOL} Successfully updated puzzle data")

        except Exception as e:
            logger.error(f"{TOOL} Failed to update puzzle data: {e}")
            return {"tool_result": [f"{TOOL}: Error: {e}"]}

        # generate tool result message
        puzzle_updated_json =await self.serialize_puzzle_obj_for_llm(puzzle_updated, model)

        ## compare puzzles and extract changes
        logger.debug(f"{TOOL} extract changes...")
        puzzle_dict = json.loads(puzzle_json)
        puzzle_updated_dict = json.loads(puzzle_updated_json)
        puzzle_changes = await self.extract_puzzle_diff(puzzle_dict, puzzle_updated_dict)
        puzzle_changes = "\n".join(puzzle_changes)
        logger.debug(f"{TOOL} Extracted changes: \n{puzzle_changes}")

        logger.debug(f"{TOOL} Generating tool response...")
        try:
            system_prompt_summary = f"""
            You are an assistant who compares this old puzzle data {puzzle_json}
            with changes. Use this {BASIC_RULES} to understand and summerize changes.
            """
            summary_prompt = {"system_prompt": system_prompt_summary, "user_prompt": puzzle_changes}
            tool_summary = await llm.chat(summary_prompt)
            if not tool_summary:
                raise Exception(f"{TOOL} Failed to generate summary data: ")

            logger.debug(f"{TOOL} Generated tool response: \n{tool_summary}")
            return {"tool_result": [f"{TOOL}: Updated puzzle successfully! {tool_summary}"]}

        except Exception as e:
            logger.error(f"{TOOL} Failed to generate tool response: {e}")
            return {"tool_result": [f"{TOOL}: Error: {e}"]}


    def ensure_uuid(self, val):
        if isinstance(val, UUID):
            return val
        if isinstance(val, str):
            return UUID(val.strip())
        return val

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
