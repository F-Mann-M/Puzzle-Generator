import operator
from typing import Annotated, List, TypedDict, Optional, Any
from uuid import UUID
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

import json
import logging
from utils.logger_config import configure_logging

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


# get logger
logger = logging.getLogger(__name__)
TOOL_DESCRIPTION = """
        chat: normal chat. Receives user messages and gives back llm response
        collect_and_create: Generates instantly a new puzzle based on the last user message
        collect_info: collects detailed information to create a puzzle. It keeps user asking until all information are collected.
        modify_puzzle: Takes in users message and updates an existing puzzle
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
            logger.info("get_history: AsyncSqliteSaver connection established.")

            # Initiate the Graph
            graph = self.workflow.compile(checkpointer=checkpointer)
            logger.info("get_history: Pass database URL to StateGraph")
            config = {"configurable": {"thread_id": str(self.session_id)}}

            # get latest state SnapShot
            logger.info("get_history: Get state history...")
            try:
                state = await graph.aget_state(config)
                logger.info("state_history loaded")

                logger.info("get_history: return messages to router")
                if state.values and "messages" in state.values:
                    return state.values["messages"]

            except Exception as e:
                logger.error(f"Error! Could not load chat history: {e}")
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
        builder.add_edge("modify_puzzle", "format_response")
        builder.add_edge("format_response", END)

        return builder


    async def _classify_intent(self, state: AgentState)-> AgentState:
        """ Classify user intent from conversation"""

        logger.info("\nClassify intent...")
        logger.info("\nCurrent State: \n"
              f"Current Puzzle ID: {state.get('current_puzzle_id')}\n"
              f"Collected Infos: {state.get('collected_info')}\n"
              f"Tool result: {state.get('tool_result')}\n")

        # Get llm
        llm = get_llm(state["model"])

        last_message = state["messages"][-1] if state["messages"] else ""

        # Get chat history
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000]  # keep the conversation short

        logger.info(f"\nClassify intent from conversation.")
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
        If something is unclear, return 'chat' to clarify."""
        # ALWAYS prefer 'modifiy' over 'create', 'create' over 'generate' and 'generate' over 'chat'.

        prompt = {
            "system_prompt": system_prompt,
            "user_prompt": last_message.get("content"),
        }

        # Simple async call
        logger.info("Analyse user's massage and classify his intent...")
        intent = await llm.chat(prompt)
        logger.info("\nLLM has classifies user intention: ", intent)

        return {
            "user_intent": intent.lower(),
            "tool_result": [], # make sure tool result is reseted
                }


    async def _intent(self, state: AgentState) -> str:
        """Got to the next node based on user intent."""
        return state.get("user_intent", "chat") # Chat by default


    async def _chat(self, state: AgentState) -> AgentState:
        """ handel ongoing chat"""
        TOOL = "Chat_agent.chat:"
        # Get llm
        llm = get_llm(state["model"])

        # Get user message
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        logger.info(f"\n{TOOL} Last message sent to llm: ", last_message)

        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000:]  # keep the conversation short
        logger.info(f"\n{TOOL} conversation: {conversation}")

        # Create prompt
        system_prompt = (
            f"""
            you are an assistant.
            Your name is Rudolfo
            If user asks for the rules of the game use {BASIC_RULES}.
            You ONLY answer questions related to the puzzle rules, how to improve puzzle, find puzzle relates solutions and patterns.
            Your ONLY purpose is to help the user with the a puzzle.
            if user asks for something not puzzle related answer in a funny way.
            Keep answers short and clear. 
            User chat history {conversation} to generate an ongoing chat.
            """)

        prompt = {"system_prompt": system_prompt, "user_prompt": last_message}

        # Get LLM response
        logger.info("loading ai response...")
        llm_response = await llm.chat(prompt)
        final_response = ""
        if llm_response:
            logger.info("loading ai response successfully")
            final_response = llm_response
        else:
            final_response = f"Ups! Something went wrong 😅 <br> Could not load the AI response from {state.get('model')}"

        # store response in state
        logger.info("Llm response: ", final_response)
        messages = [{"role": "assistant", "content": final_response}]

        return {"messages": messages}


    async def _collect_and_creates_puzzle(self, state: AgentState) -> AgentState:
        """ If LLM provides a complete puzzle, create a new puzzle """
        TOOL = "ChatAgent.collect_and_create: "
        tool_results = state.get("tool_result")

        # Get LLM
        llm = get_llm(state["model"])

        last_message = state["messages"][-1] if state["messages"] else ""

        # get conversation
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000:]  # keep the conversation short
        logger.info(f"\n{TOOL} Collect and create a new puzzle...")


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
        puzzle_generated = type[BaseModel]
        try:
            logger.info(f"\n{TOOL} Calling LLM.structured() with PuzzleLLMResponse schema...")
            puzzle_generated = await llm.structured(prompt=prompt, schema=PuzzleLLMResponse)

            if puzzle_generated is None:
                raise Exception("LLM raise None for structured data")

            logger.info(f"\n{TOOL} generated data: {puzzle_generated}")


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
                logger.info(f"\n{TOOL} Create new puzzle...")
                puzzle = self.puzzle_services.create_puzzle(puzzle_config)
                logger.info(f"\n{TOOL} New Puzzle created successfully (collect and create node)")

                # Add puzzle.id to current session
                session_id = UUID(self.session_id.strip())
                self.session_services.add_puzzle_id(puzzle.id, session_id)

                # Update state
                logger.info("\nNew Puzzle created successfully (collect and create node). Puzzle ID: ", puzzle.id)

                # Add to tool result
                tool_results.append(TOOL + str(puzzle_generated))
                tool_results.append(TOOL + f"<br>Puzzle {puzzle.name} generated successfully")

                return {
                    "tool_result": tool_results,
                    "current_puzzle_id": puzzle.id
                        }

        except Exception as e:
            logger.error(f"{TOOL} Could not create a puzzle. Error: {e}")
            puzzle_json = puzzle_generated.model_dump_json()
            tool_results.append(TOOL + puzzle_json)
            tool_results.append(TOOL + f"Could not create a puzzle. Error: {e}")

            return {"tool_result": tool_results}


    async def _collect_info(self, state: AgentState) -> AgentState:
        """ Collect all necessary information from user to create a new puzzle. """
        TOOL = "Chat_agent.collect_info:"
        logger.info(f"\n\n{TOOL} Collecting information from user to create a new puzzle...")
        last_message = state["messages"][-1] if state["messages"] else ""

        # TODO: add list for tool response

        # get last message
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000:]  # keep the conversation short
       


        logger.info(f"{TOOL} Collect info: get conversation and extract information from it...")
        system_prompt = f"""Extract puzzle generation parameters from this conversation:
                {conversation}
                Be aware of suggestions for puzzle details in the previous conversation - like name, node count, etc extract them.

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
        logger.info(f"\n {TOOL}LLM Response collects info...")
        llm_response = await llm.chat(prompt)

        # Clean the string to remove markdown backticks
        clean_json_string = llm_response.replace("```json", "").replace("```", "").strip()

        # Convert string to Python dict
        response = json.loads(clean_json_string)

        # check collected info:
        if state.get("collected_info"):
            collected_info = state.get("collected_info")
        else:
            collected_info = {
                "name": None,
                "game_mode": None,
                "node_count": None,
                "edge_count": None,
            "turns": None,
            "units": None,
            "description": " ",
            }

        is_collected = True
        # todo: check if there is at least one player and one enemy unit
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

        if missing_info:
            logger.info(f"{TOOL} missing info", missing_info)

        # Generate Puzzle or ask user for more information
        tool_response = ""
        if is_collected:
            logger.info(f"\n{TOOL} All information collected!")
            print(f"{TOOL} Collected info: ", collected_info)

            try:
                # convert to PuzzleGenerate schema
                puzzle_generated = PuzzleGenerate(
                    name=collected_info["name"],
                    model=state["model"],
                    game_mode=collected_info["game_mode"],
                    node_count=collected_info["node_count"],
                    edge_count=collected_info["edge_count"],
                    turns=collected_info["turns"],
                    units=collected_info["units"],
                    description=collected_info.get("description", "")
                )
                if not puzzle_generated:
                    raise Exception(f"{TOOL} Could not convert into PuzzleGenerate schema. Error: {e}")

                # Call Tool generate Puzzle
                logger.info(f"{TOOL} Generate Puzzle...")
                puzzle_id = await self.tools.generate_puzzle(puzzle_generated)
                if not puzzle_id:
                    raise Exception(f"{TOOL} Could not generate Puzzle.")

                tool_response = f"""{TOOL} Puzzle generated successfully"""

            except Exception as e:
                logger.error(f"{TOOL} Could not generate Puzzle. Error: {e}")
                return {"tool_result": f"{TOOL} Could not generate Puzzle. Error: {e}"}

            # Add puzzle.id to current session
            self.session_services.add_puzzle_id(puzzle_id, UUID(self.session_id))

            return {
                "current_puzzle_id": puzzle_id,
                "tool_result": tool_response
            }

        else:
            logger.info("\nfollowing infos are still missing: ")
            for info in missing_info:
                logger.info(f"\t{info}")
            tool_response = f"""{TOOL}: following infos are still missing: {", ".join(missing_info)}. Ask user for missing information"""

        # debugging
        logger.info("\n****Current State (chat 2) ******\n")
        logger.info("puzzle id: ", state.get("current_puzzle_id"))

        return {"tool_result": tool_response, "collected_info": collected_info}


    async def _modify_puzzle(self, state: AgentState) -> AgentState:
        """Updates an existing puzzle based on feedback"""
        logger.info("\nModifying Puzzle:")
        TOOL = "ChatAgent.modify: "

        # get latest message
        logger.info(f"{TOOL} Takes in user message")
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        if not last_message:
            return {"tool_result": [f"{TOOL} No messages found. Could not extract puzzle related information to modify puzzle."]}

        # Get Puzzle ID
        logger.info(f"{TOOL} load puzzle id from states...")
        puzzle_id = state.get("current_puzzle_id")
        if not puzzle_id:
            return {"tool_result": [f"{TOOL} No puzzle ID found. Can't modify without puzzle."]}

        try:
            # extract information form message and modify puzzle
            logger.info(f"{TOOL} current puzzle id: ", puzzle_id)
            logger.info(f"{TOOL} call Agent tool 'update_puzzle'...")
            tools = AgentTools(self.db)
            result = await tools.update_puzzle(
                puzzle_id=puzzle_id,
                message=last_message,
                model=state.get("model"),
                session_id=state.get("session_id"),
            )
            return result

        except Exception as e:
            return {"tool_result": [f"{TOOL} Error while loading agent tool: {e}"]}


    async def process(self, user_message: str) -> tuple[str, UUID | None]:
        """ Process user message and return response """
        logger.info("\nProcess user message: ", user_message)

        # Process with graph
        async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_URL) as checkpointer:
            graph = self.workflow.compile(checkpointer=checkpointer)
            logger.info("Invoke agent graph")
            config = {"configurable": {"thread_id": str(self.session_id)}}

            try:
                # merging new user message into LangGraph state history
                logger.info("process: Invoke graph...")
                result = await graph.ainvoke(
                    {"messages": [{"role": "user", "content": user_message}],
                    "model": self.model,
                    "session_id": str(self.session_id),
                    "tool_result": [],
                     },
                    config = config
                )

                # Extract message and puzzle id for router
                logger.info("process: Extract message and puzzle ID from StateGraph object...")
                if result["messages"]:
                    last_message = result.get("messages")[-1]
                    # to make sure to get last message even it's no dict
                    message = last_message.get("content") if isinstance(last_message, dict) else last_message.content
                current_puzzle_id = result.get("current_puzzle_id")
                logger.info("Return puzzle id to chat router (ChatAgent process): ", current_puzzle_id)
                return message, current_puzzle_id

            except Exception as e:
                logger.error("process: Error while graph processing: ", e)
                return f"process: Error while graph processing: {e}", None


    async def format_response(self, state: AgentState) -> AgentState:
        """
        Format final response from tool_result for user.
        if last used tool is chat return last message
        """
        TOOL = "ChatAgent.format_response:"
        logger.info(f"\n\n{TOOL} Format final response from tool_result... ")
        if state.get("user_intent") == "chat":
            logger.info(f"{TOOL} Chat intent - skipping format_response, using existing message")
            return

        # get tool result
        tool_result = state.get("tool_result")
        logger.info(f"format_response: tool_result: {tool_result}")
        if not tool_result:
            logger.info(f"{TOOL} tool_result is empty!")
            return {"message": "Tool result is empty!"}

        # convert tool result to string
        combined_results = "".join(tool_result)
        logger.info(f"\n{TOOL} Join all tool results: ", combined_results)

        llm = get_llm(state["model"])
        system_prompt = f"""
        You are an assistant who takes in a list of tool results {combined_results}
        Use the {BASIC_RULES} to explain modification and requests. 
        """

        try:
            # get tool_result summery from LLM
            logger.info("Send tools results to LLM...")
            prompt = {
                "system_prompt": system_prompt,
                "user_prompt": "Explain the modifications",
            }

            final_response = await llm.chat(prompt)
            messages = [{"role": "assistant", "content": final_response}]

            return {
                "messages": messages,
                "tool_result": [], # reset tool results
                    }

        except Exception as e:
            logger.error(f"{TOOL} Error while generating LLM response: {e}")
            return {"messages":
                        [{
                            "role": "assistent",
                            "content": f"{TOOL} Error while generating LLM response: {e}",
                            "tool_result": [],
                        }]
            }




