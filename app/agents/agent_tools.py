from app.schemas import PuzzleGenerate
from app.services import PuzzleServices

class AgentTools:

    def __init__(self, db):
        self.db = db

    async def generate_puzzle(self, puzzle_config: PuzzleGenerate):
        """ Generate a new puzzle"""
        services = PuzzleServices(self.db)
        puzzle_generated = await services.generate_puzzle(puzzle_config)
        new_puzzle = services.create_puzzle(puzzle_generated)
        return new_puzzle.id


    def update_puzzle(self):
        """ Update an existing puzzle"""
        pass


    def validate_puzzle(self):
        """ Validate an existing puzzle"""
        pass


    def visualize_puzzle(self): # could also be part of chat agent
        """ Visualize an existing puzzle"""
        pass


    def delete_puzzle(self):
        """ Delete an existing puzzle"""
        pass


    def generate_example_puzzle(self): # It can probably be handled by the chat agent.
        """ Generate an example puzzle"""
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

