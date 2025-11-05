from app import models
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from uuid import uuid4

from app.schemas import PuzzleCreate, NodeCreate, EdgeCreate, UnitCreate


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
            enemy_count=puzzle_data.enemy_count,
            player_unit_count=puzzle_data.player_unit_count,
            game_mode=puzzle_data.game_mode,
            node_count=puzzle_data.node_count,
            edge_count=puzzle_data.edge_count,
            coins=puzzle_data.coins,
        )
        self.db.add(puzzle)
        self.db.flush()
        return puzzle.id


    def create_nodes(self, nodes: list[NodeCreate]):
        """ Create nodes, build and return index → id map. Used to build edges"""
        node_map = {}
        for node_data in nodes:
            node = models.Node(
                id=uuid4(),
                node_index=node_data.node_index,
                x_position=node_data.x_position,
                y_position=node_data.y_position,
                puzzle_id=node_data.puzzle_id
            )
            self.db.add(node)
            self.db.flush()
            node_map[node_data.node_index] = node.id
        return node_map


    def create_edges(self, edges: list[EdgeCreate]):
        for edge_data in edges:
            edge = models.Edge(
                id=uuid4(),
                edge_index=edge_data.edge_index,
                start_node_id=edge_data.start_node_id,
                end_node_id=edge_data.end_node_id,
                puzzle_id=edge_data.puzzle_id
            )
            self.db.add(edge)
            self.db.flush()


    def create_units_with_path(self, puzzle_id, units: list[UnitCreate]):

        for unit_data in units:
            # Create Unit
            unit = models.Unit(
                id=uuid4(),
                unit_type=unit_data.unit_type,
                faction=unit_data.faction,
                puzzle_id=puzzle_id,
            )
            self.db.add(unit)
            self.db.flush()

            # Create path
            path = models.Path(unit_id=unit.id
                               )
            self.db.add(path)
            self.db.flush()

            # Create path_node
            for index, n_index in enumerate(unit_data.path_nodes):
                node = (
                    self.db.query(models.Node)
                    .filter(
                        models.Node.puzzle_id == puzzle_id,
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


    def commit_all(self):
        # Commit all
        self.db.commit()


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
                  .options(joinedload(models.Puzzle.units) # gets related units form units table
                           .joinedload(models.Unit.path) # with paths
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


    # update puzzle
    def update_puzzle(self, puzzle_id, updated_data):
        puzzle = self.get_puzzle_by_id(puzzle_id)


    # generate puzzle
    def generate_puzzle(self, puzzle_data):
        # llm = puzzle_data.model
        # prompt = self.prompts.format("puzzle_generation", **config.dict())
        # puzzle = await llm.generate(prompt)
        # return puzzle

        # prompt = self.get_dynamic_prompt(puzzle_data)
        # model_dict = {
        #     "GPT-4o-mini": self.openai_gpt_4_o_mini,
        #     "Gemini Flash 2.5": self.google_gemini_flash_2_5,
        #     "Groq": self.groq_xyz
        #     }
        # puzzle =
        # if puzzle_data.model in model_dict:
        #    puzzle = model_dict[puzzle_data.model](prompt)


        # get game rules
        # prompt rules dynamically
        # give examples
            # get data from database filtered by game mode
        # rules to return data
            # list[nodes] (x,y)
            # list[units] path
            #
        pass

    def get_dynamic_prompt(self, puzzle_data):
        pass


    def openai_gpt_4_o_mini(self, prompt):
       pass

    def google_gemini_flash_2_5(self, prompt):
        pass


    def groq_xyz(self, prompt):
        pass

