from app import models
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from uuid import uuid4

from app.schemas import PuzzleCreate, PuzzleGenerate
from app.llm import get_llm
from app.prompts.prompt_manager import get_prompt
from app.prompts.prompt_game_rules import BASIC_RULES


class PuzzleServices:
    """ Handles all puzzle related DB operation"""

    def __init__(self, db):
        self.db = db

    # create puzzle
    def create_puzzle(self, puzzle_data: PuzzleCreate):
        """Insert new puzzle to DB table puzzles and its related units"""

        puzzle = models.Puzzle(
            id=uuid4(),
            name=puzzle_data.name,
            model=puzzle_data.model,
            enemy_count=len([enemy for enemy in puzzle_data.units if enemy["faction"] == "enemy"]),
            player_unit_count=len([player for player in puzzle_data.units if player["faction"] == "player"]),
            game_mode=puzzle_data.game_mode,
            node_count=len([node for node in puzzle_data.nodes]),
            edge_count=len([edge for edge in puzzle_data.edges]),
            coins=puzzle_data.coins,
            description=puzzle_data.description,
            is_working=puzzle_data.is_working,
        )
        self.db.add(puzzle)
        self.db.flush()

        # Create nodes, build and return index → id map. Used to build edges
        node_map = {}
        for node_data in puzzle_data.nodes:
            node = models.Node(
                id=uuid4(),
                node_index=node_data["index"],
                x_position=node_data["x"],
                y_position=node_data["y"],
                puzzle_id=puzzle.id
            )
            self.db.add(node)
            self.db.flush()
            node_map[node_data["index"]] = node.id

        for edge_data in puzzle_data.edges:
            start_uuid = node_map.get(edge_data["start"])
            end_uuid = node_map.get(edge_data["end"])
            edge = models.Edge(
                id=uuid4(),
                edge_index=edge_data["index"],
                start_node_id=start_uuid,
                end_node_id=end_uuid,
                puzzle_id=puzzle.id
            )
            self.db.add(edge)
            self.db.flush()

        # Create Unit
        print("\n\nUnit properties: ", puzzle_data.units)  # debugging
        for unit_data in puzzle_data.units:
            unit = models.Unit(
                id=uuid4(),
                unit_type=unit_data["type"],
                faction=unit_data["faction"],
                puzzle_id=puzzle.id,
            )
            self.db.add(unit)
            self.db.flush()

            # Create path
            path = models.Path(unit_id=unit.id)
            self.db.add(path)
            self.db.flush()

            # Create path_node
            for index, n_index in enumerate(unit_data["path"]):
                node = (
                    self.db.query(models.Node)
                    .filter(
                        models.Node.puzzle_id == puzzle.id,
                        models.Node.node_index == n_index
                    )
                    .first()
                )
                path_node = models.PathNode(
                    id=uuid4(),
                    path_id=path.id,
                    node_id=node.id,
                    order_index=index,
                    node_index=n_index
                )
                self.db.add(path_node)
                self.db.flush()

        self.db.commit()
        return puzzle

    # get all puzzle
    def get_all_puzzle(
            self,
            name: Optional[str] = None,
            game_mode: Optional[str] = None,  # default None if no filter is selected
            model: Optional[str] = None,
            sort_by: Optional[str] = None,
            order: Optional[str] = "asc"  # default asc
    ) -> List[models.Puzzle]:  # returns a list of Puzzle objects
        """Fetch puzzle with filter"""
        query = self.db.query(models.Puzzle)

        # filter not implemented to front-end yet
        if name:
            query = query.filter(models.Puzzle.name == name)
        if game_mode:
            query = query.filter(models.Puzzle.game_mode == game_mode)
        if model:
            query = query.filter(models.Puzzle.model == model)
        if sort_by:
            sort_column = getattr(models.Puzzle, sort_by, None)
            if sort_column:
                query = query.order_by(sort_column.desc() if order == "desc" else sort_column.asc())

        puzzles = query.all()
        return puzzles


    # get one puzzle by id
    def get_puzzle_by_id(self, puzzle_id):
        """Fetch puzzle by id"""
        puzzle = (self.db.query(models.Puzzle)
                  .options(joinedload(models.Puzzle.units)  # gets related units form units table
                           .joinedload(models.Unit.path)  # with paths
                           .joinedload(models.Path.path_node))
                  .options(joinedload(models.Puzzle.nodes))  # get related nodes
                  .options(joinedload(models.Puzzle.edges))  # get related edges
                  .filter(models.Puzzle.id == puzzle_id).first())
        if not puzzle:
            raise HTTPException(status_code=404, detail="Puzzle not found")
        return puzzle


    # delete one puzzle
    def delete_puzzle(self, puzzle_id):
        """Fetch puzzle by id an delete"""
        puzzle = self.get_puzzle_by_id(puzzle_id)
        if puzzle:
            self.db.delete(puzzle)
            self.db.commit()


    def update_puzzle(self, puzzle_id, puzzle_data: PuzzleCreate):
        """Update existing puzzle by deleting old data and recreating with new data"""
        puzzle = self.get_puzzle_by_id(puzzle_id)
        if not puzzle:
            raise HTTPException(status_code=404, detail="Puzzle not found")

        # Update puzzle metadata
        puzzle.name = puzzle_data.name
        puzzle.model = puzzle_data.model
        puzzle.enemy_count = len([enemy for enemy in puzzle_data.units if enemy["faction"] == "enemy"])
        puzzle.player_unit_count = len([player for player in puzzle_data.units if player["faction"] == "player"])
        puzzle.game_mode = puzzle_data.game_mode
        puzzle.node_count = len([node for node in puzzle_data.nodes])
        puzzle.edge_count = len([edge for edge in puzzle_data.edges])
        puzzle.coins = puzzle_data.coins
        puzzle.description = puzzle_data.description
        puzzle.is_working = puzzle_data.is_working
        self.db.flush()

        # Delete old nodes, edges, and units
        for node in puzzle.nodes:
            self.db.delete(node)
        for edge in puzzle.edges:
            self.db.delete(edge)
        for unit in puzzle.units:
            self.db.delete(unit)
        self.db.flush()

        # Create new nodes, build and return index → id map
        node_map = {}
        for node_data in puzzle_data.nodes:
            node = models.Node(
                id=uuid4(),
                node_index=node_data["index"],
                x_position=node_data["x"],
                y_position=node_data["y"],
                puzzle_id=puzzle.id
            )
            self.db.add(node)
            self.db.flush()
            node_map[node_data["index"]] = node.id

        # Create new edges
        for edge_data in puzzle_data.edges:
            start_uuid = node_map.get(edge_data["start"])
            end_uuid = node_map.get(edge_data["end"])
            edge = models.Edge(
                id=uuid4(),
                edge_index=edge_data["index"],
                start_node_id=start_uuid,
                end_node_id=end_uuid,
                puzzle_id=puzzle.id
            )
            self.db.add(edge)
            self.db.flush()

        # Create new units
        for unit_data in puzzle_data.units:
            unit = models.Unit(
                id=uuid4(),
                unit_type=unit_data["type"],
                faction=unit_data["faction"],
                puzzle_id=puzzle.id,
            )
            self.db.add(unit)
            self.db.flush()

            # Create path
            path = models.Path(unit_id=unit.id)
            self.db.add(path)
            self.db.flush()

            # Create path_node
            for index, n_index in enumerate(unit_data["path"]):
                node = (
                    self.db.query(models.Node)
                    .filter(
                        models.Node.puzzle_id == puzzle.id,
                        models.Node.node_index == n_index
                    )
                    .first()
                )
                path_node = models.PathNode(
                    id=uuid4(),
                    path_id=path.id,
                    node_id=node.id,
                    order_index=index,
                    node_index=n_index
                )
                self.db.add(path_node)
                self.db.flush()

        self.db.commit()
        return puzzle


    # generate puzzle
    async def generate_puzzle(self, puzzle_config: PuzzleGenerate) -> PuzzleCreate:
        print("Puzzle Config: ", puzzle_config)

        # get example puzzles from database
        example_puzzles = self.get_all_puzzle()
        # Serialize each puzzle to JSON format
        serialized_examples = []
        for puzzle in example_puzzles:
            if puzzle.game_mode.lower() == puzzle_config.game_mode.lower() and puzzle.is_working:
                serialized = self.serialize_puzzle(puzzle.id)
                # Add description and name for context
                serialized['name'] = puzzle.name
                serialized['description'] = puzzle.description
                serialized['game_mode'] = puzzle.game_mode
                serialized_examples.append(serialized)

        llm = get_llm(puzzle_config.model)
        prompts = await get_prompt(
            example_puzzles=serialized_examples,
            db=self.db,
            game_mode=puzzle_config.game_mode,
            node_count=puzzle_config.node_count,
            edge_count=puzzle_config.edge_count,
            turns=puzzle_config.turns,
            units=puzzle_config.units,
            description=puzzle_config.description,
        )

        puzzle_generated = await llm.generate(prompts)
        print("\n\nGenerated description: ", puzzle_generated.description)  # debugging

        new_puzzle = PuzzleCreate(
            name=puzzle_config.name,
            model=puzzle_config.model,
            game_mode=puzzle_config.game_mode,
            coins=puzzle_generated.coins,
            nodes=[n.model_dump() for n in puzzle_generated.nodes],
            edges=[n.model_dump() for n in puzzle_generated.edges],
            units=[n.model_dump() for n in puzzle_generated.units],
            description=puzzle_generated.description
        )

        return new_puzzle

    # Serialize puzzle data to JSON
    def serialize_puzzle(self, puzzle_id):
        puzzle = self.get_puzzle_by_id(puzzle_id)
        puzzle_data = {
            "nodes": [
                {
                    "id": str(node.id),
                    "node_index": node.node_index,
                    "x_position": node.x_position,
                    "y_position": node.y_position
                }
                for node in sorted(puzzle.nodes, key=lambda n: n.node_index)
            ],
            "edges": [
                {
                    "edge_index": edge.edge_index,
                    "start_node_id": str(edge.start_node_id),
                    "end_node_id": str(edge.end_node_id)
                }
                for edge in sorted(puzzle.edges, key=lambda e: e.edge_index)
            ],
            "units": [
                {
                    "id": str(unit.id),
                    "unit_type": unit.unit_type,
                    "faction": unit.faction,
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
            ]
        }

        return puzzle_data


    # Get Chat data and evaluate next steps
    async def chat(self, model: str, message: str) -> str:
        llm = get_llm(model)
        system_prompt = (
            "You are an helpfully assistant."
            "you are an noble advisor."
            "You speak like a noble advisor from the Middle Ages."
            "Your name is Rudolfo"
            "You only address the user as Lord or a nobel person."
            "The users Name is Goetz. He is a robber knight."
            f"If user asks for the rules of the game use {BASIC_RULES}."
            "You ONLY answer questions related to the puzzle rules"
            "Your ONLY purpose is to help the user with the a puzzle."
            "if user asks for somthing not puzzle related answer in a funny way. make up a very short Middle Ages anecdote"
        )
        prompt = {"system_prompt": system_prompt, "user_prompt": message}
        llm_response = await llm.chat(prompt)
        return llm_response
