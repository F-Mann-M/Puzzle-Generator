import operator
from typing import Annotated, List, Literal, TypedDict, Optional, Any
from uuid import UUID
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import InMemorySaver

from app.models import Session


class AgentState(TypedDict):
    messages: Annotated[List[dict[str, str]], operator.add]

    user_intent: Optional[str] # "generate", "modify", "example", "chat"
    collect_info: dict[str, Any] # "game_mode", "node_count", "enemy_unit_count", "enemy_type", "player_unit_count"
    current_puzzle_id: Optional[UUID] # if puzzle generated and stored get id
    # tool_result: Annotated[list[str], operator.add] #
    # final_response: Optional[list]
    session_id: UUID
    model: str # model used... pass llm_manager.py

class ChatAgent:
    """ LangGraph Chat Agent to handel puzzle related content"""

    def __init__(self, db: Session, session_id: UUID, model: str) -> None:
        self.db = db
        self.session_id = session_id
        self.model = model
        self.tools = AgentTools(db)
        self.graph = self.build_graph()


    def build_graph(self) -> StateGraph:
        """ Build the LangGraph Chat Agent graph """

        builder = StateGraph(AgentState)


# state
# def nodes (tools)
# add nodes
# add edges
# compile graph
