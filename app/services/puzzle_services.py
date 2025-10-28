from app import models
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from app.schemas import PuzzleCreate


class PuzzleServices:
    """ Handles all puzzle related DB operation"""
    def __init__(self, db):
        self.db = db

    # create puzzle
    def create_puzzle(self, puzzle_data: PuzzleCreate):
        """Insert new puzzle to DB table puzzles and its related units"""
        db_puzzle = models.Puzzle(
            name=puzzle_data.name,
            model=puzzle_data.model,
            enemy_count=puzzle_data.enemy_count,
            player_unit_count=puzzle_data.player_unit_count,
            game_mode=puzzle_data.game_mode,
            node_count=puzzle_data.node_count,
            coins=puzzle_data.coins,
        )

        # Create units and store in units table
        if puzzle_data.units:
            units = [
                models.Unit(
                    unit_type = data.unit_type,
                    movement = data.movement,
                    faction = data.faction
                )
            for data in puzzle_data.units]

            db_puzzle.units = units


        self.db.add(db_puzzle)
        self.db.commit()
        self.db.refresh(db_puzzle)
        return db_puzzle


    # get all puzzle
    def get_all_puzzle(
        self,
        name: Optional[str] = None,
        game_mode: Optional[str] = None, # default None if no filter is selected
        model: Optional[str] = None,
        sort_by: Optional[str] = None,
        order: Optional[str] = "asc" # default asc
        ) -> List[models.Puzzle]: # returns a list of Puzzle objects
        """Fetch puzzle with filter"""
        query = self.db.query(models.Puzzle)

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
                  .options(joinedload(models.Puzzle.units)) # gets related units form units table
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

