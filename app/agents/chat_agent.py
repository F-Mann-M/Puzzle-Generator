import operator
from typing import Annotated, List, TypedDict, Optional, Any
from uuid import UUID
from langgraph.graph import END, START, StateGraph
import json

# MemorySave works only for sync environment
# therefor I use AsyncSqliteSaver to async store checkpoints
# but this version is currently buggy
import aiosqlite

from exercise.langgraph_exercise_01 import initial_state

# --- START FIX: Monkey Patch aiosqlite ---
# The new version of aiosqlite removed 'is_alive', but LangGraph still looks for it.
# manually add it back so the code doesn't crash.
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        # We assume if the thread is running, the connection is alive
        return self._running

    aiosqlite.Connection.is_alive = is_alive
# --- END FIX ---
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.models import Session
from app.agents.agent_tools import AgentTools
from app.llm.llm_manager import get_llm
from app.services import SessionService, PuzzleServices
from app.schemas import PuzzleCreate, PuzzleLLMResponse
from app.prompts.prompt_game_rules import BASIC_RULES
from app.core.config import settings

TOOL_DESCRIPTION = """
        chat: normal chat. Receives user messages and gives back llm response
        collect_and_create: Generates instantly a new puzzle based on the last user message
        collect_info: collects detailed information to create a puzzle. It keeps user asking until all information are collected.
        update_puzzle: Takes in users message and updates an existing puzzle
        """


class AgentState(TypedDict):
    messages: Annotated[List[dict[str, str]], operator.add]
    user_intent: Optional[str] # "generate", "create", "modify", "chat"
    collected_info: dict[str, Any] # "game_mode", "node_count", "enemy_unit_count", "enemy_type", "player_unit_count", "description"
    current_puzzle_id: Optional[UUID] # if puzzle generated and stored get id
    tool_result: List[str] # collect result messages from tools
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
        self.workflow = self.build_graph()
        self.session_services = SessionService(self.db)
        self.puzzle_services = PuzzleServices(self.db)


    def build_graph(self) -> StateGraph:
        """ Build the LangGraph Chat Agent graph """

        # Build Graph
        builder = StateGraph(AgentState)

        # Nodes
        builder.add_node("intent", self._classify_intent)
        builder.add_node("chat", self._chat)
        builder.add_node("collect_info", self._collect_info)
        builder.add_node("collect_and_create", self._collect_and_creates_puzzle)
        builder.add_node("generate", self.tools.generate_puzzle)
        builder.add_node("format_response", self.format_response)

        # Edges
        builder.add_edge(START, "intent")
        builder.add_conditional_edges("intent", self._intent,
                                      {
                                          "generate" : "collect_and_create",
                                          "create" : "collect_info", # will be collect_info
                                          "chat" : "chat",
                                          "modify": "chat" # will be update
                                      })
        builder.add_edge("collect_and_create", "format_response")
        builder.add_edge("collect_info", "format_response")
        builder.add_edge("chat", "format_response")
        builder.add_edge("format_response", END)


        return builder

    TOOL_DESCRIPTION = """
        chat: normal chat. Receives user messages and gives back llm response
        collect_and_create: Generates instantly a new puzzle based on the last user message
        collect_info: collects detailed information to create a puzzle. It keeps user asking until all information are collected.
        update_puzzle: Takes in users message and updates an existing puzzle
        """

    async def _classify_intent(self, state: AgentState)-> AgentState:
        """ Classify user intent from conversation"""

        # Get llm
        llm = get_llm(state["model"])

        last_message = state["messages"][-1] if state["messages"] else ""

        # Get chat history
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])

        print(f"\nClassify intent from conversation: {conversation}")

        system_prompt = """You are an intent classifier. Analyse user's massage and classify his intent.
        Return ONLY one word: 'generate', 'create', 'modify' and 'chat'

        - generate: The user wants to generate a new puzzle without having to provide all the necessary details.
        - create: The user wants to create a new puzzle (mentions creating, generating, new puzzle, etc.). 
        - modify: User wants to change/update the current puzzle (mentions changing, updating, fixing, improving, etc.)
        - chat: General conversation, questions about rules, or non-puzzle related chat
        
        If something is unclear, return 'chat' to clarify."""


        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": last_message.get("content"),
        }

        # Simple async call
        print("Analyse user's massage and classify his intent...")
        intent = await llm.chat(prompt)
        print("\nLLM has classifies user intention: ", intent)

        # state["user_intent"] = intent.lower()

        print("\n****Current State (intent) ******\n")
        for key, value in state.items():
            print(f"{key}: {value}")
        print("state messages: ", len(state["messages"]))

        return {"user_intent": intent.lower()}


    async def _intent(self, state: AgentState) -> str:
        """Got to the next node based on user intent."""
        return state.get("user_intent", "chat") # Chat by default


    async def _chat(self, state: AgentState) -> AgentState:
        """ handel ongoing chat"""
        # Get llm
        llm = get_llm(state["model"])

        # Get user message
        messages = state["messages"]
        last_message = state["messages"][-1] if state["messages"] else ""
        print("\nLast message sent to llm: ", last_message)

        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        print(f"\nChat conversation: {conversation}")

        # Create prompt
        system_prompt = (
            f"""You are an helpfully assistant.
            you are a noble advisor.
            Your name is Rudolfo
            You only address the user as a nobel person.
            The users Name is Goetz. He is a robber knight.
            The users Character is based on the knight Götz von Berlichen
            If user asks for the rules of the game use {BASIC_RULES}.
            You ONLY answer questions related to the puzzle rules or Middle Ages.
            You can tell a bit about the medieval everyday life,
            you can make up funny gossip from Berlichenstein Castle, 
            medieval war strategies, anecdotes from the 'Three-Legged Chicken' tavern.
            Your ONLY purpose is to help the user with the a puzzle.
            if user asks for somthing not puzzle related answer in a funny way. 
            make up a very short Middle Ages anecdote
            User the chat history {conversation} to stay in an ongoing conversation.
            """)

        prompt = {"system_prompt": system_prompt, "user_prompt": last_message.get("content")}

        # Get LLM response
        print("loading ai response...")
        llm_response = await llm.chat(prompt)
        final_response = ""
        if llm_response:
            print("loading ai response successfully")
            final_response = llm_response
        else:
            final_response = f"Ups! Something went wrong 😅 <br> Could not load the AI response from {state.get('model')}"

        # store response in state
        print("Llm response: ", final_response)
        messages = [{"role": "assistant", "content": final_response}]

        # Debugging
        print("\n****Current State (chat 2) ******\n")
        for key, value in state.items():
            print(f"{key}: {value}")
        print("state messages: ", len(state["messages"]))

        return {"messages": messages}


    async def _collect_and_creates_puzzle(self, state: AgentState) -> AgentState:
        """ If LLM provides a complete puzzle, create a new puzzle """
        TOOL = "collect_and_create: "
        tool_results = state["tool_results"]

        # Get LLM
        llm = get_llm(state["model"])

        last_message = state["messages"][-1] if state["messages"] else ""

        # get conversation
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        print("\nCollect and create conversation: ", conversation)
        print("\nCollect and create a new puzzle...")


        system_prompt = f"""
                        You are a puzzle-generation agent.
                        This are the puzzle rules {BASIC_RULES}

                        You MUST output a single JSON object that strictly conforms to the provided JSON Schema.

                        Rules:
                        - Output JSON only.
                        - Do NOT include explanations, markdown, or commentary.
                        - Do NOT include code fences.
                        - Do NOT include trailing text.
                        - The response must be directly parseable as JSON.
                        - Add detail description what happens turn by turn in 'description'

                        
                        If you cannot produce valid JSON, output an empty JSON object: {{}}

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

        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": last_message.get("content"),
        }

        # Simple async call
        raw_data = await llm.chat(prompt)
        print("\nLLM Response collected puzzle info to create puzzle: ", raw_data)

        try:
            # convert to JSON Object
            puzzle_generated = PuzzleLLMResponse.model_validate_json(raw_data)

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
                state["tool_result"].append(TOOL + raw_data)
                state["tool_result"].append(TOOL + f"<br>Puzzle {puzzle.name} generated successfully")

                # debugging
                print("\n****Current State (chat 2) ******\n")
                for key, value in state.items():
                    print(f"{key}: {value}")
                print("state messages: ", len(state["messages"]))

                return {"tool_result": tool_results}

        except Exception as e:
            print(f"Could not create a puzzle. Error: {e}")
            state["tool_result"].append(TOOL + raw_data)
            state["tool_result"].append(TOOL + f"Could not create a puzzle. Error: {e}")

            # debugging
            print("\n****Current State (chat 2) ******\n")
            for key, value in state.items():
                print(f"{key}: {value}")
            print("state messages: ", len(state["messages"]))

            return {"tool_result": tool_results}


    async def _collect_info(self, state: AgentState) -> AgentState:
        """ Collect information about the agent """
        TOOL = "collect_info"
        last_message = state["messages"][-1] if state["messages"] else ""

        # get last message
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        print("\nCollecting information...")
        print("\nConversation length: ", len(conversation))


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
                    "description": "any additional instructions like a special wish from user"
                }}

                Return ONLY valid JSON, no explanations."""

        llm = get_llm(state["model"])
        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": last_message.get("content"),
        }

        # Simple async call
        print("\nLLM Response collects info")
        llm_response = await llm.chat(prompt)

        #TODO: Add Schema for output

        # Clean the string to remove markdown backticks
        clean_json_string = llm_response.replace("```json", "").replace("```", "").strip()

        # Convert string to Python dict
        response = json.loads(clean_json_string)

        # check collected info:
        collected_info = {}
        is_collected = True
        missing_info = []
        for key, info in response.items():
            if info is None:
                is_collected = False
                missing_info.append(key)
            else:
                collected_info[key] = info

        print("\nCollected info: ", collected_info)

        # Generate Puzzle or ask user for more information
        tool_response = ""
        if is_collected:
            print("\nAll information collected!")
            print("Collected info: ", missing_info)
            print("Generate Puzzle...")
            # Call Tool generate Puzzle
            tool_response = f"""{TOOL}: Puzzle generated successfully"""
        else:
            print("\nfollowing infos are still missing: ")
            for info in missing_info:
                print(f"\t{info}")
            tool_response = f"""{TOOL}: following infos are still missing: {", ".join(missing_info)}. Ask user for missing information"""

        # # Add tool results to tool_results
        # print("\nAdd tool results to tool result...")
        # state["tool_result"] = [tool_response]
        # print("\n+++ Tool result List +++ \n", state["tool_result"])

        # debugging
        print("\n****Current State (chat 2) ******\n")
        for key, value in state.items():
            print(f"{key}: {value}")
        print("state messages: ", len(state["messages"]))

        return {"tool_result": tool_response, "collected_info": collected_info}


    async def process(self, user_message: str) -> str:
        """ Process user message and return response """
        print("\nProcess user message: ", user_message)

        # Process with graph
        async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_URL) as checkpointer:
            graph = self.workflow.compile(checkpointer=checkpointer)

            print("Invoke agent graph")
            config = {"configurable": {"thread_id": self.session_id}}
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": user_message}],
                "model": self.model,
                "session_id": self.session_id,
                "tool_result": []},
                config = config)

        print("\n****Current State (Process) ******\n", result)
        print("state messages: ", len(result.get("messages")))
        return result.get("messages")[-1]["content"] if result["messages"] else "How can I help you?"


    async def format_response(self, state: AgentState) -> AgentState:
        """
        Format final response from tool_result for user.
        if last used tool is chat return last message
        """
        print("\n\nFormat final response from tool_result... ")
        if state.get("user_intent") == "chat":
            print("Chat intent - skipping format_response, using existing message")
            return

        llm = get_llm(state["model"])
        system_prompt = f"""
        You are an assistant who takes in a list of different tool results. If tools require more information 
        ask user for detail information.
        """

        response_parts = ""
        if state.get("tool_result"):
            for result in state["tool_result"]:
                response_parts += f"{result}"
            print("\nJoin all tool results: ", response_parts)

            # get tool_result summery from LLM
            print("Send tools results to LLM...")
            prompt = {
                "system_prompt": system_prompt,
                "user_prompt": response_parts,
            }
            final_response = await llm.chat(prompt)
            messages = [{"role": "assistant", "content": final_response}]

            # Debugging
            print("\n****Current State (Format) ******\n")
            for key, value in state.items():
                print(f"{key}: {value}")
            print("state messages: ", len(state["messages"]))
            print("\n\n")

            return {"messages": messages}
        else:
            print("\nNo tool result found.")

        print("\n****Current State (Format) ******\n")
        for key, value in state.items():
            print(f"{key}: {value}")
        print("state messages: ", len(state["messages"]))
        print("\n\n")
        return {}






