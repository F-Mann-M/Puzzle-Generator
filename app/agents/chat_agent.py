import operator
from typing import Annotated, List, TypedDict, Optional, Any
from uuid import UUID
from langgraph.graph import END, START, StateGraph
from langchain_core.runnables import RunnableConfig

import json

# MemorySave works only for sync environment
# therefor I use AsyncSqliteSaver to async store checkpoints
# but this version is currently buggy
import aiosqlite

# --- START FIX: Monkey Patch aiosqlite ---
# The new version of aiosqlite removed 'is_alive', but LangGraph still looks for it.
# manually add it back so the code doesn't crash.
if not hasattr(aiosqlite.Connection, "is_alive"):
    def is_alive(self):
        return self._running
    aiosqlite.Connection.is_alive = is_alive
# --- END FIX ---

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.models import Session
from app.agents.agent_tools import AgentTools
from app.llm.llm_manager import get_llm
from app.services import SessionService, PuzzleServices
from app.schemas import PuzzleCreate, PuzzleLLMResponse, PuzzleGenerate
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


    async def get_history(self):
        """Load current chat history from LangGraph checkpointer"""

        async with (AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_URL) as checkpointer):
            print("get_history: AsyncSqliteSaver connection established.")

            # Initiate the Graph
            graph = self.workflow.compile(checkpointer=checkpointer)
            print("get_history: Pass database URL to StateGraph")
            config = {"configurable": {"thread_id": str(self.session_id)}}
            # config = RunnableConfig(
            #     configurable={"thread_id": str(self.session_id)})
            print("get_history: Configure state graph/pass session ID as thread ID")

            # get latest state SnapShot
            print("get_history: Get state history...")
            try:
                state = await graph.aget_state(config)
                print("state_history loaded", state)

                print("get_history: return messages to router")
                if state.values and "messages" in state.values:
                    return state.values["messages"]

            except Exception as e:
                print(f"Error! Could not load chat history: {e}")
                error_message = f"Error while getting chat history: {e}"

                return [{"role": "assistant", "content": error_message}]


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
        builder.add_node("modify_puzzle", self._modify_puzzle)

        # Edges
        builder.add_edge(START, "intent")
        builder.add_conditional_edges("intent", self._intent,
                                      {
                                          "generate" : "collect_and_create",
                                          "create" : "collect_info",
                                          "chat" : "chat",
                                          "modify": "modify_puzzle"
                                      })
        builder.add_edge("collect_and_create", "format_response")
        builder.add_edge("collect_info", "format_response")
        builder.add_edge("chat", "format_response")
        builder.add_edge("format_response", END)

        return builder


    async def _classify_intent(self, state: AgentState)-> AgentState:
        """ Classify user intent from conversation"""

        print("\nClassify intent...")
        print(f"\nCurrent State: \n"
              f"Current Puzzle ID: {state.get('current_puzzle_id')}\n"
              f"Collected Infors: {state.get('collected_info')}\n")

        # Get llm
        llm = get_llm(state["model"])

        last_message = state["messages"][-1] if state["messages"] else ""

        # Get chat history
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000]  # keep the conversation short

        print(f"\nClassify intent from conversation.")
        intent_create = (" - create: The user wants to create a new puzzle "
                         "(mentions creating, new puzzle, nodes is..., edges should be...). ")
        intent_generate = "- generate: The user wants to generate a new puzzle without having to provide all the necessary details."
        intent_modify = ("- modify: User wants to change/update the current puzzle "
                         "(mentions changing, updating, fixing, improving, add, delete, remove, currently etc.)")
        intent_chat = "- chat: General conversation, questions about rules, or non-puzzle related chat"
        intention = ""

        # If there is already a puzzle make sure to modify the existing puzzle
        if state.get("current_puzzle_id"):
            intention = ("'modify', 'chat'\n\n"
                         f"{intent_modify}\n"
                         f"{intent_chat}\n")
        # When there are already collected puzzle data but no puzzle id make sure to go on with puzzle creation
        elif state.get("collected_info") and not state.get("current_puzzle_id"):
            intention = ("'create', 'chat'\n\n"
                         f"{intent_create}\n"
                         f"{intent_chat}\n")
        # When there is no puzzle and no collected data try to figur out what user wants.
        else:
            intention = ("'create', 'generate' and 'chat'\n\n"
                         f"{intent_generate}\n"
                         f"{intent_chat}\n"
                         f"{intent_create}")


        system_prompt = f"""You are an intent classifier. Analyse user's massage and classify his intent.
        Return ONLY one word: {intention}
        ALWAYS prefer 'modifiy' over 'create', 'create' over 'generate' and 'generate' over 'chat'.
        If something is unclear, return 'chat' to clarify."""

        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": last_message.get("content"),
        }

        # Simple async call
        print("Analyse user's massage and classify his intent...")
        intent = await llm.chat(prompt)
        print("\nLLM has classifies user intention: ", intent)

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
        if len(conversation) > 3000:
            conversation = conversation[-3000]  # keep the conversation short
        # print(f"\nChat conversation: {conversation}")

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
            make up a very short Middle Ages anecdote.
            Always be positive and polite, but with a sarcastic, humorous undertone.
            When the user asks questions or makes statements, mention how great and wise his questions are with a humorous, slightly ironic undertone.
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

        return {"messages": messages}


    async def _collect_and_creates_puzzle(self, state: AgentState) -> AgentState:
        """ If LLM provides a complete puzzle, create a new puzzle """
        TOOL = "collect_and_create: "
        tool_results = state.get("tool_result")

        # Get LLM
        llm = get_llm(state["model"])

        last_message = state["messages"][-1] if state["messages"] else ""

        # get conversation
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000]  # keep the conversation short
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
                session_id = UUID(self.session_id.strip())
                self.session_services.add_puzzle_id(puzzle.id, session_id)

                # Update state
                print("\nNew Puzzle created successfully (collect and create node). Puzzle ID: ", puzzle.id)

                # Add to tool result
                tool_results.append(TOOL + raw_data)
                tool_results.append(TOOL + f"<br>Puzzle {puzzle.name} generated successfully")

                return {
                    "tool_result": tool_results,
                    "current_puzzle_id": puzzle.id
                        }

        except Exception as e:
            print(f"Could not create a puzzle. Error: {e}")
            tool_results.append(TOOL + raw_data)
            tool_results.append(TOOL + f"Could not create a puzzle. Error: {e}")

            return {"tool_result": tool_results}


    async def _collect_info(self, state: AgentState) -> AgentState:
        """ Collect information about the agent """
        TOOL = "collect_info"
        last_message = state["messages"][-1] if state["messages"] else ""

        # get last message
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000]  # keep the conversation short
        print("conversation: ", conversation)
        print("\nCollecting information...")
        print("\nConversation length (character length): ", len(conversation))


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
                
                description is optional
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
        #ToDo: use structured output

        # Clean the string to remove markdown backticks
        clean_json_string = llm_response.replace("```json", "").replace("```", "").strip()

        # Convert string to Python dict
        response = json.loads(clean_json_string)

        # check collected info:
        if state.get("collected_info"): # ToDo: create an initial state in session_services
            collected_info = state.get("collected_info")
        else:
            collected_info = {
                "name": None,
                "game_mode": None,
                "node_count": None,
                "edge_count": None,
            "turns": None,
            "units": None,
            "description": " "
            }

        is_collected = True
        has_enemy_unit = False
        has_player_unit = False
        missing_info = []
        for key, info in response.items():
            if info is not None:
                collected_info[key] = info

        # check collected info:
        for key, info in collected_info.items():
            if info is None:
                is_collected = False
                missing_info.append(key)

        print("\nCollected info: ", collected_info)

        # Generate Puzzle or ask user for more information
        tool_response = ""
        if is_collected:
            print("\nAll information collected!")
            print("Collected info: ", missing_info)
            print("Generate Puzzle...")

            # convert to PuzzleGenerate
            puzzle_generated = PuzzleGenerate(
                name=collected_info["name"],
                model=state["model"],
                game_mode=collected_info["game_mode"],
                node_count=collected_info["node_count"],
                edge_count=collected_info["edge_count"],
                turns=collected_info["turns"],
                units=collected_info["units"],
                description=collected_info["description"]
            )

            # Call Tool generate Puzzle
            puzzle_id = await self.tools.generate_puzzle(puzzle_generated)
            tool_response = f"""{TOOL}: Puzzle generated successfully"""

            # Add puzzle.id to current session
            self.session_services.add_puzzle_id(puzzle_id, UUID(self.session_id))

            return {
                "current_puzzle_id": puzzle_id,
                "tool_result": tool_response
            }

        else:
            print("\nfollowing infos are still missing: ")
            for info in missing_info:
                print(f"\t{info}")
            tool_response = f"""{TOOL}: following infos are still missing: {", ".join(missing_info)}. Ask user for missing information"""

        # debugging
        print("\n****Current State (chat 2) ******\n")
        print("puzzle id: ", state.get("current_puzzle_id"))

        return {"tool_result": tool_response, "collected_info": collected_info}


    async def _modify_puzzle(self, state: AgentState) -> AgentState:
        """Updates an existing puzzle based on feedback"""
        print("\nModifying Puzzle:")
        TOOL = "modify: "
        tool_response = state.get("tool_result") # load list []

        # get latest message
        print("modify_puzzle: Takes in user message")
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        if not last_message:
            tool_response.append(f"{TOOL} No messages found. Could not extract puzzle related information to modify puzzle.")
            return {"tool_result": tool_response}

        # Get Puzzle ID
        print("modify_puzzle: load puzzle id from states...")
        puzzle_id = state.get("current_puzzle_id")

        if not puzzle_id:
            tool_response.append(f"{TOOL} No puzzle ID found. Can't modify without puzzle.")
            return {"tool_result": tool_response}

        try:
            # extract information form message and modify puzzle
            print("modify_puzzle: current puzzle id: ", puzzle_id)
            print("modify_puzzle: call Agent tool 'update_puzzle'...")
            tools = AgentTools(self.db)
            result = await tools.update_puzzle(
                puzzle_id=puzzle_id,
                message=last_message,
                model=state.get("model"),
            )
        except Exception as e:
            tool_response.append(f"{TOOL} Error while loading agent tool: {e}")
            return {"tool_result": tool_response}

        return {"tool_result": result.get("tool_result")}



    async def process(self, user_message: str) -> tuple[str, UUID | None]:
        """ Process user message and return response """
        print("\nProcess user message: ", user_message)

        # Process with graph
        async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_URL) as checkpointer:
            graph = self.workflow.compile(checkpointer=checkpointer)
            print("Invoke agent graph")
            config = {"configurable": {"thread_id": str(self.session_id)}}

            try:
                # merging new user message into LangGraph state history
                print("process: Invoke graph...")
                result = await graph.ainvoke(
                    {"messages": [{"role": "user", "content": user_message}],
                    "model": self.model,
                    "session_id": str(self.session_id),
                    "tool_result": [],
                     },
                    config = config
                )

                # Extract message and puzzle id for router
                print("process: Extract message and puzzle ID from StateGraph object...")
                if result["messages"]:
                    last_message = result.get("messages")[-1]
                    # to make sure to get last message even it's no dict
                    message = last_message.get("content") if isinstance(last_message, dict) else last_message.content
                current_puzzle_id = result.get("current_puzzle_id")
                print("Return puzzle id to chat router (ChatAgent process): ", current_puzzle_id)
                return message, current_puzzle_id

            except Exception as e:
                print("process: Error while graph processing: ", e)
                return f"process: Error while graph processing: {e}", None


    async def format_response(self, state: AgentState) -> AgentState:
        """
        Format final response from tool_result for user.
        if last used tool is chat return last message
        """
        print("\n\nFormat final response from tool_result... ")
        if state.get("user_intent") == "chat":
            print("Chat intent - skipping format_response, using existing message")
            return

        # get tool result
        tool_result = state.get("tool_result")
        print(f"format_response: tool_result: {tool_result}")
        if not tool_result:
            print("format_response: tool_result is empty!")
            return {"message": "Tool result is empty!"}

        # convert tool result to string
        response_parts = ""
        for result in tool_result:
            response_parts += f"\n{result} "
        print("\nJoin all tool results: ", response_parts)

        llm = get_llm(state["model"])
        system_prompt = f"""
        You are an assistant who takes in a list of different tool results {response_parts}.
        Your name is Rudolfo. 
        You are a chivalrous advisor from the Middle Ages. Always be positive and polite, but with a sarcastic, humorous undertone.
        Mention how greate the plans of users are.
        If tools require more information ask the user for more detail information. 
        For further information about the puzzle use {BASIC_RULES}
        """

        try:
            # get tool_result summery from LLM
            print("Send tools results to LLM...")
            prompt = {
                "system_prompt": system_prompt,
                "user_prompt": response_parts,
            }

            final_response = await llm.chat(prompt)
            messages = [{"role": "assistant", "content": final_response}]

            return {"messages": messages} # since the state["messages"] has an LangGraph reducer message is appended to state

        except Exception as e:
            print(f"format_response: Error while generating LLM response: {e}")
            return {"messages":
                        [{
                            "role": "assistent",
                            "content": f"format_response: Error while generating LLM response: {e}"
                        }]
            }




