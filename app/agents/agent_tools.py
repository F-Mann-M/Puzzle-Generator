import json
from langgraph.types import Command
from langgraph.graph import END
from langchain.chat_models import init_chat_model
from deepdiff import DeepDiff # to check differences in changed puzzles
from app.prompts.prompt_game_rules import BASIC_RULES
from app.schemas import PuzzleGenerate, PuzzleCreate

from app.llm.llm_manager import get_llm
from uuid import UUID
from typing import Any, Union
from app.models import Puzzle
import logging
logger = logging.getLogger(__name__)


class AgentTools:

    def __init__(self, db):
        self.db = db

    async def generate_puzzle(self, puzzle_config: PuzzleGenerate) -> UUID:
        """ Generate a new puzzle"""
        from app.services import PuzzleServices
        services = PuzzleServices(self.db)
        puzzle_generated = await services.generate_puzzle(puzzle_config)

        if puzzle_generated is None:
            raise Exception("agent_tool.generate_puzzle: Failed to generate puzzle data from LLM.")

        new_puzzle = services.create_puzzle(puzzle_generated)
        return new_puzzle.id


    async def _get_node_index(self, node_id, puzzle) -> Union[int, dict]:
        """Take in node ID and Puzzle Object and return index of node with node_id"""

        current_tool = "agent_tools.generate_puzzle:"
        logger.debug(f"Start/End node ID: {node_id}")
        for node in puzzle.nodes:
            if str(node.id) == str(node_id):
                logger.debug(f"{current_tool} Node ID: {node.id} matches with node ID: {node_id}")
                return node.node_index
        logger.warning(f"{current_tool} No index found for node {node_id}")
        return {"tool_result": "can not find index"}


    async def serialize_puzzle_obj_for_llm(self, puzzle: Puzzle, model) -> json:
        """Serialize a Puzzle object to LLM readable json"""
        current_tool = "agent_tools.serialize_puzzle_obj_for_llm:"

        current_puzzle = Puzzle
        logger.debug(f"{current_tool} serialise puzzle...")
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
            #print(f"{current_tool} puzzle serialised")

        except Exception as e:
            logger.error(f"{current_tool} Error serialising puzzle: {e}")


        # convert puzzle into JSON
        try:
            logger.info(f"{current_tool} convert to JSON...")
            current_puzzle_json = json.dumps(current_puzzle)
            return current_puzzle_json

        except Exception as e:
            logger.error(f"{current_tool} Error converting puzzle: {e}")


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
            session_id: Union[UUID, str]) ->  Command:
        """ Update an existing puzzle"""
        current_tool = "update_puzzle: "
        logger.info(f"{current_tool} Takes in current puzzle data and message: {message}")

        # Ensure puzzle_id is a UUID object, not a string
        puzzle_id = self.ensure_uuid(puzzle_id)

        # Get puzzle data
        from app.services import PuzzleServices
        puzzle_services = PuzzleServices(self.db)
        logger.debug(f"{current_tool} Get puzzle by ID")
        try:
            # get puzzle by id
            puzzle = puzzle_services.get_puzzle_by_id(puzzle_id)
        except Exception as e:
            logger.error(f"{current_tool} Error fetching puzzle: {e}")
            return {f"tool_result": [f"{current_tool} Error fetching puzzle: {e}"]}

        # Serialise puzzle data
        puzzle_json = await self.serialize_puzzle_obj_for_llm(puzzle, model)

        # update existing puzzle
        llm = init_chat_model(
            model,
            model_provider="google_genai" if model.startswith("gemini") else None
        )
        system_prompt = f"""
        You are an assistant who extracts puzzle modification parameters from this message.
        
        ### CURRENT PUZZLE CONTEXT ###
            {puzzle_json}
        ##############################
        
        ### PUZZLE RULES ###
            {BASIC_RULES}
        ####################
        
        Analyse the existing puzzle context data above.
        Use the existing puzzle data to understand what kind of data have do added, deleted, changed or modified.
        
        Use the puzzle rules to understand how the puzzle works and what and how it has to be modified.
        Mind the rules above while adding modifications to the existing puzzle data.
        
        If the user asks to generate a description.
        Analyse the given puzzle data and rules to generate a detailed description of the current puzzle what happens turn by turn .
        Add the description to 'description' field of the current puzzle.
        
        Return ONLY a valid JSON object conforming to this Pydantic schema: {PuzzleCreate}
        """
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        logger.info(f"{current_tool} Extracting data from user message and modifying existing puzzle data...")
        try:
            updated_puzzle_llm = llm.with_structured_output(PuzzleCreate)
            updated_puzzle_data = await updated_puzzle_llm.ainvoke(prompt)
            if not updated_puzzle_data:
                logger.error(f"{current_tool} Failed to generate modified puzzle data")
                raise Exception("Failed to generate modified puzzle data")

            puzzle_updated = None
            if updated_puzzle_data:
                logger.info(f"{current_tool} Updating current puzzle data...")
                puzzle_updated = puzzle_services.update_puzzle(
                    puzzle_id=puzzle_id,
                    puzzle_data=updated_puzzle_data)
                if not puzzle_updated:
                    raise Exception(f"{current_tool} Failed to update existing puzzle data.")

            logger.info(f"{current_tool} Successfully updated puzzle data")

        except Exception as e:
            logger.error(f"{current_tool} Failed to update puzzle data: {e}")
            return {"tool_result": [f"{current_tool} Error: {e}"]}

        # generate tool result message
        logger.info(f"Generate tool result:")
        puzzle_updated_json = await self.serialize_puzzle_obj_for_llm(puzzle_updated, model)
        if not puzzle_updated_json:
            logger.error(f"{current_tool} convert to json failed")
            return {"tool_result": [f"{current_tool}: convert to json failed"]}

        ## compare puzzles and extract changes
        try:
            logger.info(f"{current_tool} extract changes...")

            # convert old puzzle from json to dict
            puzzle_dict = json.loads(puzzle_json)
            if not puzzle_dict:
                raise Exception("Failed to convert 'puzzle_json' to puzzle_dic")

            # convert updated puzzle json to dict
            puzzle_updated_dict = json.loads(puzzle_updated_json)
            if not puzzle_updated_dict:
                raise Exception("Failed to convert 'puzzle_json' to puzzle_dic")

            # extract differences from old and new puzzle
            puzzle_changes = await self.extract_puzzle_diff(puzzle_dict, puzzle_updated_dict) # extract differences
            puzzle_changes = "\n".join(puzzle_changes) # join differences (list) to string
            if not puzzle_changes:
                raise Exception("Failed to extract differences from puzzle_dict and puzzle_updated_dict")

            logger.info(f"{current_tool} Extracted changes: {puzzle_changes}")

        except Exception as e:
            logger.error(f"{current_tool} Failed to extract changes: {e}")
            return {"tool_result": [f"{current_tool} Failed to extract changes: {e}"]}

        logger.info(f"{current_tool} Generating tool response...")
        try:
            system_prompt_summary = f"""
            
            ### OLD PUZZLE CONTEXT ###
                {puzzle_json}
                
            ### PUZZLE RULES ###
                {BASIC_RULES}
             
            You are an assistant who compares the old puzzle data from above with this changes. 
            Use the puzzle rules to understand what has changed and how this effects the puzzle.
            List in brief bullet points what has been changed and how it affects the puzzle.
            """
            summary_prompt = [
                {"role": "system", "content": system_prompt_summary},
                {"role": "system", "content": puzzle_changes}
            ]

            tool_summary = await llm.ainvoke(summary_prompt)
            if not tool_summary:
                raise Exception(f"{current_tool} Failed to generate summary data: ")

            logger.info(f"{current_tool} Generated tool response: \n{tool_summary}")
            message = [{"role": "assistant", "content": tool_summary}]
            return Command(
                update={"messages":  message},
                goto=END
            )

        except Exception as e:
            logger.error(f"{current_tool} Failed to generate tool response: {e}")
            return {"tool_result": [f"{current_tool}: Failed to generate tool response: {e}"]}


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

