import operator
from typing import Annotated, List, TypedDict, Optional, Any
from uuid import UUID
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
import json
import logging
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import uuid
import re
import markdown

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

from sqlalchemy.orm import Session
from app.agents.agent_tools import AgentTools
from app.services import PuzzleServices, SessionService
from app.schemas import PuzzleCreate, PuzzleLLMResponse, PuzzleGenerate
from app.prompts.prompt_game_rules import BASIC_RULES
from app.core.config import settings
from app import models

load_dotenv()

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
    puzzle: Optional[str] # serialized puzzle

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
            logger.debug(f"get_history: current session id: {self.session_id}")

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
                else:
                    return None

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
        # builder.add_edge("chat", "format_response")
        builder.add_edge("modify_puzzle", "format_response")
        builder.add_edge("format_response", END)

        return builder


    async def _classify_intent(self, state: AgentState)-> AgentState:
        """ Classify user intent from conversation"""

        logger.info("\n\nClassify intent...")
        logger.info("\nCurrent State: \n"
              f"Current Puzzle ID: {state.get('current_puzzle_id')}\n"
              f"Collected Infos: {state.get('collected_info')}\n"
              f"Tool result: {state.get('tool_result')}\n"
              f"Puzzle: {bool(state.get('puzzle'))}\n")

        # Get llm
        llm = init_chat_model(
            state["model"],
            model_provider="google_genai" if state["model"].startswith("gemini") else None
        )

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

        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": last_message.get("content")}
        ]

        # Simple async call
        try:
            logger.info("Analyse user's massage and classify his intent...")
            response = await llm.ainvoke(prompt)
            intent = response.content

            return {
                "user_intent": intent.lower(),
                "tool_result": [],  # make sure tool result is reseted
            }

        except Exception as e:
            logger.error(f"Error while classifying intent:  {e}")
            return {"tool_result": [f"Error while classifying intent: {e}"]}




    async def _intent(self, state: AgentState) -> str:
        """Got to the next node based on user intent."""
        return state.get("user_intent", "chat") # Chat by default


    async def _chat(self, state: AgentState) -> AgentState:
        """ handel ongoing chat"""
        current_tool = "Chat_agent.chat:"

        # get puzzle state
        puzzle_context = state.get("puzzle")
        if not puzzle_context or puzzle_context == {}:
            puzzle_context = "No puzzle data loaded. Ask the user to create or select a puzzle."

        collected_data = state.get("collected_info")
        if not collected_data or collected_data == {}:
            collected_data = "No collected data yet."

        # Get user message
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        logger.info(f"\nLast message sent to llm: {last_message}")

        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000:]  # keep the conversation short
        logger.info(f"\n conversation length: {len(conversation)}")

        # Create prompt
        system_prompt = (
            f"""
           You are an AI Game Designer assistant.
            
            ### CURRENT PUZZLE CONTEXT ###
            {puzzle_context}
            ##############################
            
            ### Collected puzzle Data ###
            {collected_data}
            #############################

            Your Goal:
            1. Answer questions about the puzzle above (layout, units, pathing).
            2. Suggest improvements based on these Rules: {BASIC_RULES}.
            3. If the user asks to "describe" the puzzle, analyze the 'nodes', 'edges', and 'units' in the Context above and generate a strategic summary.
            4. if the user asks for collected puzzle data use the collected data from above.

            Constraints:
            - Do NOT output JSON unless explicitly asked.
            - Keep answers helpful, clear, and concise.
            - If the context is empty, ask the user to select a puzzle.
            
            #### CURRENT CONVERSATION ###
            {conversation}
            #############################
            
            User the conversation above to generate an ongoing chat.
            """)

        prompt = [{"role": "system", "content": system_prompt,},{"role": "user", "content": last_message}]

        # Get llm
        llm = init_chat_model(
            state["model"],
            model_provider="google_genai" if state["model"].startswith("gemini") else None
        )


        # Get LLM response
        logger.info("loading ai response...")

        try:
            llm_response = await llm.ainvoke(prompt)
            final_response = ""
            if llm_response:
                logger.info("loading ai response successfully")
                final_response = llm_response.content
            else:
                final_response = f"Ups! Something went wrong 😅 <br> Could not load the AI response from {state.get('model')}"

            # store response in state
            logger.info(f"Llm response: {final_response}")
            messages = [{"role": "assistant", "content": final_response}]

            # for some reason Command seams to have a conflict with static graph
            return {"messages": messages}

        except Exception as e:
            logger.info(f"Could not load LLM chat response: {e}")
            return Command(
                update={"tool_result": f"Chat: Could not load LLM chat response: {e}"},
                goto="format_response"
            )


    async def _collect_and_creates_puzzle(self, state: AgentState) -> AgentState:
        """ If LLM provides a complete puzzle, create a new puzzle """
        current_tool = "collect_and_create: "
        tool_results = state.get("tool_result")

        # Get LLM
        llm = init_chat_model(
            state["model"],
            model_provider="google_genai" if state["model"].startswith("gemini") else None
        )

        last_message = state["messages"][-1] if state["messages"] else ""

        # get conversation
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 2000:
            conversation = conversation[-2000:]  # keep the conversation short
        logger.info(f"\n{current_tool} Collect and create a new puzzle...")

        # get example puzzles from database
        example_puzzles = self.db.query(models.Puzzle).filter(models.Puzzle.is_working == True).all()

        if not example_puzzles:
            logger.error(f"Could not get example puzzles.")

        # Serialize each puzzle to JSON format to use it as examples in few shot prompt
        puzzle_services = PuzzleServices(self.db)

        serialized_examples = []

        for puzzle in example_puzzles:
            puzzle_json = await self.tools.serialize_puzzle_obj_for_llm(puzzle, self.model)
            serialized_examples.append(puzzle_json)

        system_prompt = f"""
            You are a Master Level Designer. Your goal is NOT just to generate valid JSON, but to extract puzzle data from the conversation and create a 'Fun and Balanced' tactical puzzle.

            ### What makes a puzzle fun? ###
            1. **Trial-and-Error**: Obscures the one correct solution so that the player is forced to go through many possible paths like a chess player
            2. **Dependencies**: All elements of the puzzle are pieces of the solution. Instead of creating isolated tasks in a puzzle, link them together.
            3. **Flanking Routes**: Create main paths and side paths.
            4. **Asymmetry**: Don't just mirror the map. Give the enemy the high ground or numbers advantage.
            
            ### Instructions ###
            1. Extract puzzle data from the conversation
            2. First, conceive a theme (e.g., "The Ambush", "The Bridge Defense").
            3. Explain the intended strategy for the player in the 'description' field.
            4. FINALLY, generate the nodes and units to match that strategy.
            
            ### Puzzle Rules ###
            {BASIC_RULES}
            1. This are the puzzle rules analyze them carefully.
            2. find and develop special patterns to force the player to think like a chess player
            3. Use them to generate a working puzzle based on this rules
                        
            if the user hasn't specified the game mode use 'skirmish' as default mode
            You will create all nodes, edges, and paths for enemy units and player units.
            Since the paths of the player units are also the solution of each puzzle, you must provide the puzzle with the solution (how to place and move player units).            
            
            ### Formating
            You must always output valid JSON matching the PuzzleLLMResponse schema exactly.
            
            ### JSON Schema Definitions (TypeScript)
            
            interface PuzzleLLMResponse {{
              name: string; // make up a name for the puzzle
              nodes: NodeGenerate[];
              edges: EdgeGenerate[];
              units: UnitGenerate[];
              coins: number;
              description: string; // Describe moves in detail turn by turn. Use \\n for new paragraphs.
            }}
            
            interface NodeGenerate {{
              index: number;
              x: number;
              y: number;
            }}
            
            interface EdgeGenerate {{
              index: number; // Must be an integer
              start: number; // Index of the start node
              end: number;   // Index of the end node
              // STRICTLY FORBIDDEN: Do NOT include 'x' or 'y' in edges.
            }}
            
            interface UnitGenerate {{
              type: string;
              faction: string;
              path: number[]; // List of node indices
            }}
            
            ### Constraints
            1. Return ONLY a valid JSON object conforming to the schema above.
            2. Return no explanations, only raw JSON.
            3. For Edges: strictly use keys 'index', 'start', 'end'. 
            4. Do NOT use aliases like 'from', 'to', 'source', 'target'.
            5. Do NOT include coordinates (x, y) in Edges.
            6. Ensure each list is a JSON array ([...]), not an object with keys.
            
            ### Examples
            {serialized_examples}
            
            These are example puzzles in JSON format. 
            Use these examples as reference for structure and puzzle design patterns."""

        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation},
        ]

        # Simple async call
        puzzle_generated = None

        try:
            logger.info(f"\n{current_tool} Calling LLM.structured() with PuzzleLLMResponse schema...")
            puzzle_generated_llm = llm.with_structured_output(PuzzleLLMResponse)
            puzzle_generated = await puzzle_generated_llm.ainvoke(prompt)

            if puzzle_generated is None:
                raise Exception("LLM raise None for structured data")

            logger.info(f"\n{current_tool} generated data: {puzzle_generated}")


            puzzle_config = PuzzleCreate(
                name=puzzle_generated.name if puzzle_generated.name else "Generated Puzzle", # ToDo: generate puzzle name
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
                logger.info(f"\n{current_tool} Create new puzzle...")
                puzzle = self.puzzle_services.create_puzzle(puzzle_config)
                logger.info(f"\n{current_tool} New Puzzle created successfully (collect and create node)")

                # Add puzzle.id to current session
                session_id = UUID(self.session_id.strip())
                self.session_services.add_puzzle_id(puzzle.id, session_id)

                # Update state
                logger.info(f"\nNew Puzzle created successfully (collect and create node). Puzzle ID: {puzzle.id}")

                # Add to tool result
                tool_results.append(f"{current_tool} Puzzle {puzzle.name} generated successfully")

                return {
                    "tool_result": tool_results,
                    "current_puzzle_id": str(puzzle.id) if puzzle.id else None
                        }

        except Exception as e:
            logger.error(f"{current_tool} Could not create a puzzle. Error: {e}")
            tool_results.append(current_tool + f"Could not create a puzzle. Error: {e}")

            return {"tool_result": tool_results}


    async def _collect_info(self, state: AgentState) -> AgentState | Command:
        """ Collect all necessary information from user to create a new puzzle. """
        current_tool = "Chat_agent.collect_info:"
        logger.info(f"\n\n{current_tool} Collecting information from user to create a new puzzle...")
        last_message = state["messages"][-1] if state["messages"] else ""

        # TODO: add list for tool response

        # get last message
        conversation = "\n".join([f"{message['role']}: {message['content']}" for message in state["messages"]])
        if len(conversation) > 3000:
            conversation = conversation[-3000:]  # keep the conversation short
       

        logger.info(f"{current_tool} Collect info: get conversation and extract information from it...")
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
                        {{"type": "Grunt" or "Swordsman", "faction": "enemy" or "player", "count": 2}},
                    ],
                    "description": "any additional instructions like a special wish from user"
                }}
                
                description is optional
                Return ONLY valid JSON, no explanations."""

        llm = init_chat_model(
            state["model"],
            model_provider="google_genai" if state["model"].startswith("gemini") else None
        )

        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": last_message.get("content")}
        ]

        # Simple async call
        logger.info(f"\n {current_tool}LLM Response collects info...")
        llm_response = await llm.ainvoke(prompt)
        llm_response_str = llm_response.content

        # Clean the string to remove markdown backticks
        clean_json_string = llm_response_str.replace("```json", "").replace("```", "").strip()

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
        has_enemy_unit = False
        has_player_unit = False
        missing_info = []
        for key, info in response.items():
            if info is not None:
                collected_info[key] = info
                if key == "units":
                    # check if there is at least 1 player and one enemy unit
                    for unit in info:
                        if unit.get("faction") == "player":
                            has_player_unit = True
                        if unit.get("faction") == "enemy":
                            has_enemy_unit = True

        # check collected info:
        for key, info in collected_info.items():
            if info is None:
                is_collected = False
                missing_info.append(key)

        if not has_player_unit:
            missing_info.append("player unit")

        if not has_enemy_unit:
            missing_info.append("enemy unit")

        if missing_info:
            logger.info(f"{current_tool} missing info {missing_info}")

        # Generate Puzzle or ask user for more information
        tool_response = ""
        if is_collected and has_player_unit and has_enemy_unit:
            logger.info(f"\n{current_tool} All information collected!")
            print(f"{current_tool} Collected info: {collected_info}")

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
                    raise Exception(f"{current_tool} Could not convert into PuzzleGenerate schema. Error")

                # Call Tool generate Puzzle
                logger.info(f"{current_tool} Generate Puzzle...")
                puzzle_id = await self.tools.generate_puzzle(puzzle_generated)
                if not puzzle_id:
                    raise Exception(f"{current_tool} Could not generate Puzzle.")

                tool_response = f"""{current_tool} Puzzle generated successfully"""

            except Exception as e:
                logger.error(f"{current_tool} Could not generate Puzzle. Error: {e}")
                return {"tool_result": f"{current_tool} Could not generate Puzzle. Error: {e}"}

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
            tool_response = f"""{current_tool} following infos are still missing: {", ".join(missing_info)}. Ask user for missing information"""

        # debugging
        logger.info("\n****Current State (chat 2) ******\n")
        logger.info(f"puzzle id: {state.get('current_puzzle_id')}")

        return {"tool_result": tool_response, "collected_info": collected_info}


    async def _modify_puzzle(self, state: AgentState) -> AgentState:
        """Updates an existing puzzle based on feedback"""
        logger.info("\nModifying Puzzle:")
        current_tool = "ChatAgent.modify: "

        # get latest message
        logger.info(f"{current_tool} Takes in user message")
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        if not last_message:
            return {"tool_result": [f"{current_tool} No messages found. Could not extract puzzle related information to modify puzzle."]}

        # Get Puzzle ID
        logger.info(f"{current_tool} load puzzle id from states...")
        puzzle_id = state.get("current_puzzle_id")
        if not puzzle_id:
            return {"tool_result": [f"{current_tool} No puzzle ID found. Can't modify without puzzle."]}

        try:
            # extract information form message and modify puzzle
            logger.info(f"{current_tool} current puzzle id: {puzzle_id}")
            logger.info(f"{current_tool} call Agent tool 'update_puzzle'...")
            tools = AgentTools(self.db)
            result = await tools.update_puzzle(
                puzzle_id=puzzle_id,
                message=last_message,
                model=state.get("model"),
                session_id=state.get("session_id"),
            )

            # to avoid conflict with static graph return only if result command
            if isinstance(result, Command):
                return result

            else:
                logger.info(f"tool result {result.get('tool_result')}")
                return result

        except Exception as e:
            return {"tool_result": [f"{current_tool} Error while loading agent tool: {e}"]}


    async def process(self, user_message: str, puzzle_json: str, puzzle_id: UUID) -> tuple[str, UUID | None]:
        """ Process user message and return response """
        current_tool = "ChatAgent.process:"
        logger.info(f"\n{current_tool} Process user message: {user_message}")


        # Process with graph
        async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_URL) as checkpointer:
            graph = self.workflow.compile(checkpointer=checkpointer)
            logger.info("Invoke agent graph")
            config = {"configurable": {"thread_id": str(self.session_id)}}

            # get latest state SnapShot
            logger.info("get puzzle current state")
            current_puzzle = ""

            state = await graph.aget_state(config)
            logger.info("state_history loaded")

            if state.values and "puzzle" in state.values:
                if puzzle_json and puzzle_json != state.values["puzzle"]:
                    current_puzzle = state.values["puzzle"]
                else:
                    logger.info(f"puzzle state updated.")
                    current_puzzle = puzzle_json


            try:
                # merging new user message into LangGraph state history
                logger.info(f"{current_tool} Invoke graph...")
                result = await graph.ainvoke(
                    {"messages": [{"role": "user", "content": user_message}],
                    "model": self.model,
                    "session_id": str(self.session_id),
                    "tool_result": [],
                    "puzzle": [current_puzzle] if current_puzzle else [],
                    "current_puzzle_id": str(puzzle_id) if puzzle_id else None,
                     },
                    config = config
                )

                # Extract message and puzzle id for router
                logger.info(f"{current_tool}  Extract message and puzzle ID from StateGraph object...")
                if result["messages"]:
                    last_message = result.get("messages")[-1]
                    # to make sure to get last message even it's no dict
                    message = last_message.get("content") if isinstance(last_message, dict) else last_message.content
                current_puzzle_id = result.get("current_puzzle_id")
                logger.info(f"{current_tool} Return puzzle id to chat router: {current_puzzle_id}")
                return message, current_puzzle_id

            except Exception as e:
                logger.error(f"{current_tool} Error while graph processing: {e}")
                return f"process: Error while graph processing: {e}", None


    async def process_streaming(self, user_message: str, puzzle_json: str, puzzle_id: UUID):
        """ Process user message and return response """
        current_tool = "process_streaming:"
        logger.info(f"\n{current_tool} Process user message: {user_message}")


        # Process with graph
        async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_URL) as checkpointer:
            graph = self.workflow.compile(checkpointer=checkpointer)
            logger.info("Invoke agent graph")
            config = {"configurable": {"thread_id": str(self.session_id)}}


            # generate id for reasoning
            reasoning_id = f"reasoning-{uuid.uuid4()}"
            final_content_id = f"final-{uuid.uuid4()}"

            # Setup Graph
            async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_URL) as checkpointer:
                graph = self.workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": str(self.session_id)}}

                # load states
                state = await graph.aget_state(config)
                current_puzzle = ""
                if state.values and "puzzle" in state.values:
                    if puzzle_json and puzzle_json != state.values["puzzle"]:
                        current_puzzle = state.values["puzzle"]
                    else:
                        current_puzzle = puzzle_json

                inputs = {
                    "messages": [{"role": "user", "content": user_message}],
                    "model": self.model,
                    "session_id": str(self.session_id),
                    "tool_result": [],
                    "puzzle": [current_puzzle] if current_puzzle else [],
                    "current_puzzle_id": str(puzzle_id) if puzzle_id else None,
                }

                # steam html chunks
                yield f"""
                        <div class="ai_response">
                            <details class="reasoning-block" open>
                                <summary class="reasoning-summary">
                                    Thinking Process (Click to toggle)
                                </summary>
                                <div id="{reasoning_id}" class="reasoning-content"></div>
                            </details>
                            <div id="{final_content_id}" class="final-answer"></div>
                        </div>
                        """

                is_answering = False
                final_nodes = ["chat", "format_response"]

                async for event in graph.astream_events(inputs, config, version="v2"):
                    kind = event["event"]
                    meta = event.get("metadata", {})
                    node_name = meta.get("langgraph_node", "")

                    append_html = ""

                    # status update
                    if kind == "on_chain_start" and event["name"] == "LangGraph":
                        append_html = '<div class="agent-step">▶ Starting Agent...</div>'

                    ## show current node
                    elif kind == "on_node_start" and node_name and node_name != "LangGraph":
                        append_html = f'<div class="agent-step">Step: {node_name}</div>'

                    ## show event
                    elif kind == "on_tool_start":
                        append_html = f'<div class="agent-tool">Using tool: {event["name"]}</div>'


                    elif kind == "on_tool_end":
                        output = str(event.get("data", {}).get("output"))
                        if len(output) > 200: output = output[:200] + "..."
                        safe_output = output.replace('"', '&quot;').replace("'", "&#39;")
                        append_html = f'<div class="tool-result">Result: {safe_output}</div>'

                    ## status reasoning
                    if append_html:
                        safe_html = append_html.replace("`", "\\`")
                        yield f'<script>document.getElementById("{reasoning_id}").insertAdjacentHTML("beforeend", `{safe_html}`);</script>'

                    ## streaming content
                    elif kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content

                        if content:
                            safe_content = content.replace("`", "\\`").replace("${", "\\${")

                            if node_name in final_nodes:
                                is_answering = True

                                # Stream directly into Final Answer div via Script
                                formatted_content = safe_content.replace("\n", "<br>")
                                yield f'<script>document.getElementById("{final_content_id}").insertAdjacentHTML("beforeend", `{formatted_content}`);</script>'
                            else:
                                # Internal thoughts -> Reasoning Block
                                span_html = f'<span class="internal-thought">{safe_content}</span>'
                                yield f'<script>document.getElementById("{reasoning_id}").insertAdjacentHTML("beforeend", `{span_html}`);</script>'

                # final block (formated)
                if not is_answering:
                    final_state = await graph.aget_state(config)
                    last_msg = None
                    if final_state.values and "messages" in final_state.values:
                        last_msg = final_state.values["messages"][-1]

                    content = ""
                    if last_msg:
                        content = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content")

                    if content:
                        # Render nice markdown for the final result
                        html_content = markdown.markdown(content, extensions=['extra', 'sane_lists'])
                        safe_html = html_content.replace("`", "\\`")
                        yield f'<script>document.getElementById("{final_content_id}").innerHTML = `{safe_html}`;</script>'
                    else:
                        yield f'<script>document.getElementById("{final_content_id}").innerHTML = `<div class="error">No response generated.</div>`;</script>'


    async def format_response(self, state: AgentState) -> AgentState:
        """
        Format final response from tool_result for user.
        if last used tool is chat return last message
        """

        current_tool = "format_response:"
        logger.info(f"\n\n{current_tool} Format final response from tool_result... ")
        logger.info(f"Tool result: {state['tool_result']}")

        # get tool result
        tool_result = state.get("tool_result")
        logger.info(f"format_response: tool_result: {tool_result}")
        if not tool_result:
            logger.info(f"{current_tool} tool_result is empty!")
            return {"message": "Tool result is empty!"}

        # convert tool result to string
        combined_results = "".join(tool_result)
        logger.info(f"\n{current_tool} Join all tool results: {combined_results}")

        llm = init_chat_model(
            state["model"],
            model_provider="google_genai" if state["model"].startswith("gemini") else None
        )

        system_prompt = f"""
        You are an assistant who summerized and explains the tool results to the user.
        - if there a puzzle modifications explain what is changed and how it effects the puzzle
        - If there is a demand for more information just ask the user for the information.
        - If there is an error explain the user what just happened.
        - use the tool description just for your own understanding to explain an error better.
        
        ### TOOL DESCRIPTION ###
        {TOOL_DESCRIPTION}
        
        ### LIST OF TOOL RESULTS ###
        {combined_results}
        
        ### PUZZLE CONTEXT ###
        {BASIC_RULES}
        
        ### CONSTRAINS
        Do NOT explain puzzle rules in detail.
        Do NOT explain the tools himself in detail.
        Don't talk about 'the tools'
        Keep the summerize clean and short.
       
        """

        try:
            # get tool_result summery from LLM
            logger.info("Send tools results to LLM...")
            prompt = [
                {"role": "system", "content" : system_prompt},
                {"role": "user", "content": "Give back tool results in a clean understandable way."},
            ]

            final_response = await llm.ainvoke(prompt)

            if final_response:
                logger.info(f"Return final tool result: {final_response.content}")

                messages = [{"role": "assistant", "content": final_response.content}]
                return {
                    "messages": messages,
                    "tool_result": [], # reset tool results
                        }

        except Exception as e:
            logger.error(f"{current_tool} Error while generating LLM response: {e}")
            return {"messages":
                        [{
                            "role": "assistent",
                            "content": f"{current_tool} Error while generating LLM response: {e}",
                            "tool_result": [],
                        }]
            }




