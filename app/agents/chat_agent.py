import operator
from typing import Annotated, List, Literal, TypedDict, Optional, Any, Dict
from uuid import UUID
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt, Interrupt
from langgraph.checkpoint.memory import InMemorySaver

from app.models import Session
from app.agents.agent_tools import AgentTools
from app.llm.llm_manager import get_llm
from app.services import SessionService, PuzzleServices
from app.schemas import PuzzleCreate, PuzzleLLMResponse

memory = InMemorySaver()

class AgentState(TypedDict):
    messages: Annotated[List[dict[str, str]], operator.add]
    user_intent: Optional[str] # "generate", "create", "modify", "chat"
    collected_info: dict[str, Any] # "game_mode", "node_count", "enemy_unit_count", "enemy_type", "player_unit_count", "description"
    current_puzzle_id: Optional[UUID] # if puzzle generated and stored get id
    tool_result: Annotated[List[str], operator.add] # collect result messages from tools
    final_response: Optional[str] # final response for user
    session_id: UUID
    model: str # model used... pass llm_manager.py

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
        self.puzzle_services = PuzzleServices(self.db)


    def build_graph(self) -> StateGraph:
        """ Build the LangGraph Chat Agent graph """

        # Build Graph
        builder = StateGraph(AgentState)

        # Nodes
        builder.add_node("intent", self._classify_intent)
        builder.add_node("chat", self._chat)
        # builder.add_node("collect_info", self._collect_info)
        builder.add_node("collect_and_create", self._collect_and_creates_puzzle)
        #builder.add_node("generate", self.tools.generate_puzzle)
        builder.add_node("format_response", self.format_response)

        # Edges
        builder.add_edge(START, "intent")
        builder.add_conditional_edges("intent", self._intent,
                                      {
                                          "generate" : "collect_and_create",
                                          #"create" : "collect_info",
                                          "chat" : "chat"
                                      })
        builder.add_edge("collect_and_create", "format_response")
        builder.add_edge("chat", "format_response")
        builder.add_edge("format_response", END)

        return builder.compile()

    async def _classify_intent(self, state: AgentState)-> AgentState:
        """ Classify user intent from conversation"""

        #Get conversation
        conversation = ""
        if state["messages"]:
            # message: {"id": UUID, "session_id", UUID, "role": "Rudolfo", "content": "bla bla", }
            conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])

        system_prompt = """You are an intent classifier. Analyse user's massage and classify his intent.
        Return ONLY one word: 'generate', 'create', 'modify' and 'chat'

        - generate: The user wants to generate a new puzzle without having to provide all the necessary details.
        - create: The user wants to create a new puzzle (mentions creating, generating, new puzzle, etc.). 
        - modify: User wants to change/update the current puzzle (mentions changing, updating, fixing, improving, etc.)
        - chat: General conversation, questions about rules, or non-puzzle related chat
        
        If something is unclear, return 'chat' to clarify."""

        llm = get_llm(state["model"])
        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": conversation
        }
        print("Analyse user's massage and classify his intent...")

        # Simple async call
        intent = await llm.chat(prompt)
        print("\nLLM has classifies user intention: ", intent)

        state["user_intent"] = intent.lower()
        return state

    async def _intent(self, state: AgentState) -> str:
        """Got to the next node based on user intent."""
        return state.get("user_intent", "chat") # Chat by default


    async def _chat(self, state: AgentState) -> AgentState:
        """ handel ongoing chat"""

        last_message = state["messages"][-1] if state["messages"] else ""
        print("Last message sent to llm: ", last_message)

        llm_response = await self.session_services.get_llm_response(last_message.get("content"), self.model, self.session_id)
        print("Llm response: ", llm_response)
        state["messages"] = [{"role": "Rudolfo", "content": llm_response}]

        print("current State (chat): ", state)
        return state


    async def _collect_and_creates_puzzle(self, state: AgentState) -> AgentState:
        """ If LLM provides a complete puzzle, create a new puzzle """

        # get last message
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        print("\n Conversation (state['messages']): ")

        system_prompt = f"""
                        You are a puzzle-generation agent.

                        You MUST output a single JSON object that strictly conforms to the provided JSON Schema.

                        Rules:
                        - Output JSON only.
                        - Do NOT include explanations, markdown, or commentary.
                        - Do NOT include code fences.
                        - Do NOT include trailing text.
                        - The response must be directly parseable as JSON.
                        - Add detail description what happens turn by turn in 'description'

                        
                        If you cannot produce valid JSON, output an empty JSON object: {{}}
                        
                        Extract puzzle creation parameters from this conversation: {conversation}

                        Extract and return a JSON schema: {PuzzleLLMResponse}
                        Core Schema Definitions: 
                        {{
                          "nodes": [NodeGenerate],
                          "edges": [EdgeGenerate],
                          "units": [UnitGenerate],
                          "coins": int
                          "description": str
                        }}
                        Return ONLY valid JSON, no explanations."""

        llm = get_llm(state["model"])
        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": conversation
        }

        # Simple async call
        raw_data = await llm.chat(prompt)
        print("\nLLM Response collected puzzle info to create puzzle: ", raw_data)

        # convert to JSON Object
        puzzle_generated = PuzzleLLMResponse.model_validate_json(raw_data)

        try:
            puzzle_config = PuzzleCreate(
                name="Generated Puzzle", # ToDo: generate puzzle name
                model=self.model,
                game_mode="Skirmish", # ToDo: collect game mode
                coins=puzzle_generated.coins,
                nodes=[n.model_dump() for n in puzzle_generated.nodes],
                edges=[n.model_dump() for n in puzzle_generated.edges],
                units=[n.model_dump() for n in puzzle_generated.units],
                description=puzzle_generated.description
            )
            if puzzle_config:
                # Create new puzzle and store to database
                print("\nCreate new puzzle (collect and create node)...")
                puzzle = self.puzzle_services.create_puzzle(puzzle_config)
                print("\nNew Puzzle created successfully (collect and create node)")

                # Add puzzle.id to current session
                self.session_services.add_puzzle_id(puzzle.id, self.session_id)

                # Update state
                print("\nNew Puzzle created successfully (collect and create node). Puzzle ID: ", puzzle.id)
                state["current_puzzle_id"] = puzzle.id

                # Add to tool result
                state["tool_result"].append(f"Puzzle {puzzle.name} generated successfully")

                return state
                # go to format response and chat
                # state

        except Exception as e:
            print(f"Could not create a puzzle. Error: {e}")
            state["tool_result"].append(f"Could not create a puzzle. Error: {e}")
            return state


    async def _collect_info(self, state: AgentState) -> AgentState:
        """ Collect information about the agent """

        # get last message
        conversation = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
        print("\n Conversation (state['messages']): ")

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

    async def process(self, user_message: str) -> Optional[AgentState]:
        """ Process user message and return response """
        print("Process user message: ", user_message)
        initial_state = {
            "messages": [{"role": "User", "content": user_message}],
            "model": self.model,
            "session_id": self.session_id,
            "user_intent": None,
            "collected_info": {},
            "current_puzzle_id": None,
            "tool_result": [],
            "final_response": None
        }


        # Process with graph
        print("Invoke agent graph")
        config = {"configurable": {"thread_id": self.session_id}}
        result = await self.graph.ainvoke(initial_state, config=config)

        return result.get("final_response", "How can I help you?")


    def format_response(self, state: AgentState) -> str:
        """ Format final response from tool_result for user"""

        response_parts = ""
        if state["tool_result"]:
            for result in state["tool_result"]:
                response_parts += f"{result}\n"
            state["final_response"] = response_parts if response_parts else "How can I help you?"
            state["messages"] = [{"role": "Rudolfo", "content": state["final_response"]}]
        else:
            state["final_response"] = state["messages"][-1]["content"]
        return state






