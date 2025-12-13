import operator
from typing import Annotated, List, Literal, TypedDict, Optional, Any, Dict
from uuid import UUID
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt, Interrupt
from langgraph.checkpoint.memory import InMemorySaver

from app.models import Session
from app.agents.agent_tools import AgentTools
from app.llm.llm_manager import get_llm
from app.services import SessionService

memory = InMemorySaver()

class AgentState(TypedDict):
    messages: Annotated[List[dict[str, str]], operator.add]

    user_intent: Optional[str] # "generate", "modify", "example", "chat"
    collected_info: dict[str, Any] # "game_mode", "node_count", "enemy_unit_count", "enemy_type", "player_unit_count", "description"
    current_puzzle_id: Optional[UUID] # if puzzle generated and stored get id
    # tool_result: Annotated[list[str], operator.add] #
    # final_response: Optional[list]
    session_id: UUID
    model: str # model used... pass llm_manager.py
    #final_response: Optional[str]

class ChatAgent:
    """ LangGraph Chat Agent to handel puzzle related content"""
    print("Initialize chat agent")
    def __init__(self, db: Session, session_id: str, model: str) -> None:
        self.db = db
        self.session_id = session_id
        self.model = model
        self.tools = AgentTools(db)
        self.graph = self.build_graph()
        self.session_services = SessionService(self.db)


    def build_graph(self) -> StateGraph:
        """ Build the LangGraph Chat Agent graph """

        # Build Graph
        builder = StateGraph(AgentState)

        # Nodes
        builder.add_node("chat", self._chat)
        builder.add_node("collect_info", self._collect_info)

        # Edges
        builder.add_edge(START, "chat")
        builder.add_edge("chat", "collect_info")
        builder.add_edge("collect_info", END)

        return builder.compile()


    async def _chat(self, state: AgentState) -> str:
        """ handel ongoing chat"""

        last_message = state["messages"][-1] if state["messages"] else ""
        print("Last message sent to llm: ", last_message)

        # chat_messages = self.session_services.get_session_messages(self.session_id)

        llm_response = await self.session_services.get_llm_response(last_message.get("content"), self.model, self.session_id)
        print("Llm response: ", llm_response)
        state["messages"] = [{"role": "Rudolfo", "content": llm_response}]

        return state


    async def _collect_info(self, state: AgentState) -> AgentState:
        """ Collect information about the agent """

        # get last message
        conversation = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
        print("Collect info: get conversation and extract information from it")
        system_prompt = f"""Extract puzzle generation parameters from this conversation:
                {conversation}

                Extract and return a JSON object with these fields (use null if not mentioned):
                {{
                    "name": "puzzle name",
                    "game_mode": "skirmish" or "safe_travel",
                    "node_count": number,
                    "edge_count": number (optional, can be null),
                    "turns": number,
                    "units": [
                        {{"type": "Grunt", "faction": "enemy", "count": 2}},
                        {{"type": "Swordsman", "faction": "player", "count": 1}}
                    ],
                    "description": "any additional instructions"
                }}

                Return ONLY valid JSON, no explanations."""

        llm = get_llm(state["model"])
        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": conversation
        }

        # Simple async call
        response = await llm.chat(prompt)
        print("\n LLM Response collected info")

        collected = response

        state["collected_info"] = collected
        print("\n Updated collected info of AgentState: ", state["collected_info"])
        return state

    async def process(self, user_message: str):
        """ Process user message and return response """
        print("Process user message: ", user_message)
        initial_state = {
            "messages": [{"role": "User", "content": user_message}],
            "model": self.model,
            "session_id": self.session_id,
            "user_intent": None,
            "collected_info": {},
            "current_puzzle_id": None,
        }

        # Process with graph
        print("Invoke agent graph")
        config = {"configurable": {"thread_id": self.session_id}}
        result = await self.graph.ainvoke(initial_state, config=config)

        return result["messages"][1]["content"]



