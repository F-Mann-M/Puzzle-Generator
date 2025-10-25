from app import models
from typing import List, Optional
from fastapi import HTTPException

from app.schemas import PuzzleCreate


class PuzzleServices:
    """ Handles all puzzle related DB operation"""
    def __init__(self, db):
        self.db = db

    # create puzzle
    def create_puzzle(self, puzzle_data: PuzzleCreate):
        """Insert new puzzle to DB table puzzles"""
        db_puzzle = models.Puzzle(**puzzle_data.model_dump())  # converts Pydantic object (Puzzle model) into a dict and unpacks dict into keyword arguments
        self.db.add(db_puzzle)
        self.db.commit()
        self.db.refresh(db_puzzle)
        return db_puzzle


    # get all puzzle
    def get_all_puzzle(
        self,
        game_mode: Optional[str] = None, # default None if no filter is selected
        model: Optional[str] = None,
        sort_by: Optional[str] = None,
        order: Optional[str] = "asc" # default asc
        ) -> List[models.Puzzle]: # returns a list of Puzzle objects
        """Fetch puzzle with filter"""
        query = self.db.query(models.Puzzle)

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
        puzzle = self.db.query(models.Puzzle).filter(models.Puzzle.id == puzzle_id)
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
        return {"detail": "Puzzle deleted"}

    # update puzzle

