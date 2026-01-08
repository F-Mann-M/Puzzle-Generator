from fastapi import APIRouter, Depends, Request, Body, Response, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from uuid import UUID
import markdown
from typing import Optional

from app.core.database import get_db
from app.schemas import ChatFromRequest
from app.services import SessionService, PuzzleServices
from app.agents import ChatAgent

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()


@router.get("/chat/editor", response_class=HTMLResponse)
async def get_integrated_editor(
        session_id: Optional[str] = Query(default=None),
        db: Session = Depends(get_db),
        request: Request = None
):
    """Loads Puzzle Editor"""
    # when there is no session yet load empty editor (create button instead update)
    if not session_id or session_id.strip() == "":
        return templates.TemplateResponse(
            "/create-puzzle.html",
            {
                "request": request,
            }
        )

    try:
        # manual conversion
        session_uuid = UUID(session_id.strip())
    except (ValueError, TypeError):
        return HTMLResponse(content="<div>Invalid session format.</div>")


    session_services = SessionService(db)
    puzzle_id = session_services.get_puzzle_id(session_uuid)

    if not puzzle_id:
        print("No puzzle found")

    puzzle_services = PuzzleServices(db)
    puzzle = puzzle_services.get_puzzle_by_id(puzzle_id)

    return templates.TemplateResponse(
        "partials/editor_partial.html",
        {
            "request": request,
            "puzzle": puzzle,
        }
    )


# load puzzle id for visualization
# @router.get("/chat/visualize", response_class=HTMLResponse)
# async def get_puzzle_by_session_id(
#         session_id: Optional[str] = Query(default=None),
#         db: Session = Depends(get_db)):
#     """Get current puzzle id via session_id"""
#
#     print("get puzzle: session id from chat.html: ", session_id)
#
#     # Handle empty string
#     if not session_id or session_id.strip() == "" or session_id is None:
#         return HTMLResponse(content="<div>Select a session to view the puzzle.</div>")
#
#     try:
#         # convert session id manually
#         if session_id:
#             session_uuid = UUID(session_id.strip())
#         else:
#             return
#     except (ValueError, TypeError) as e:
#         print(f"Invalid session id: {session_id}, error: {e}")
#         return HTMLResponse(content=f'<div><style color="red">Invalid session ID: {e}.</style></div>')

    #
    # # Fetch the puzzle from database/service
    # session_services = SessionService(db)
    # current_puzzle_id = session_services.get_puzzle_id(session_uuid)
    # if current_puzzle_id:
    #     print("Get puzzle id for visualization: ", current_puzzle_id)
    #
    #
    # # If no puzzle is found, return a placeholder
    # if not current_puzzle_id:
    #     return HTMLResponse(content="<div>No puzzle yet.</div>")
    #
    # try:
    #     # Fetch puzzle
    #     puzzle_services = PuzzleServices(db)
    #     puzzle = puzzle_services.get_puzzle_by_id(current_puzzle_id)
    # except Exception as e:
    #     print(f"Error fetching puzzle {e}")
    #     return HTMLResponse(content="<div>No puzzle yet.</div>")
    #
    # # Return the HTML/SVG string
    # print("return puzzle visualization")
    # return HTMLResponse(content=f'<strong>Name:</strong> {puzzle.name}<br>'
    #                             f'<strong>Game Mode:</strong> {puzzle.game_mode}<br>'
    #                             f'<svg id="puzzle-visualization-svg" data-puzzle-id="{current_puzzle_id}" style="width: 100%; min-height: 400px;"></svg>'
    #                             f"<strong>Description:</strong><br>{puzzle.description}<br>"
    #                     )

# load chat
@router.get("/chat", response_class=HTMLResponse)
async def show_chat(request: Request, db: Session = Depends(get_db)):
    """Get chat page and load all sessions."""
    services = SessionService(db)
    all_sessions = services.get_all_sessions()

    latest_session = 0
    if all_sessions:
        lastest_session = services.get_latest_session()
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "all_sessions": all_sessions,
            "lastest_session_id": lastest_session,
        }
    )


# Load sidebar as single page
@router.get("/chat/sidebar", response_class=HTMLResponse)
async def get_sidebar(#
        request: Request,
        session_id: Optional[str] = Query(None),
        db: Session = Depends(get_db)):
    """Get chat sidebar by session id, reload in separate html"""

    print("reload all sessions...")
    services = SessionService(db)
    all_sessions = services.get_all_sessions()

    return templates.TemplateResponse(
        "partials/chat_sidebar_items.html", {
            "request": request,
            "all_sessions": all_sessions,
            "latest_session_id": session_id,
        }
    )


# load session
@router.get("/chat/{session_id}", response_class=HTMLResponse)
async def get_session(session_id: UUID, db: Session = Depends(get_db)):
    """Get chat history by session id """
    print("session id from chat.html: ", session_id)

    # Initialize ChatAgent
    agent = ChatAgent(db, str(session_id), "gpt-4o-mini") # Use gpt-40-mini as default value

    # Load states from LangGraph checkpointer
    state_history = await agent.get_history()

    if not state_history:
        return HTMLResponse(content="Session has no content yet.")

    message_html = ""
    for message in state_history:
        # Access by key because LangGraph history uses dicts or message objects
        role = message.get("role") if isinstance(message, dict) else message.type
        content = message.get("content") if isinstance(message, dict) else message.content

        if role == "user":
            message_html += f'<div class="user_message"><strong>You:</strong> {content}</div>'
        else:
            message_content = markdown.markdown(content)
            message_html += f'<div class="ai_response"><strong>Rudolfo:</strong> {message_content}</div>'

    return HTMLResponse(content=message_html)


# Chat
@router.post("/chat", response_class=HTMLResponse)
async def chat(
    chat_data: ChatFromRequest = Body(...),  # parse from JSON body
    db: Session = Depends(get_db),
    response: Response = Response(), # visualize puzzle container ask for puzzle update
):
    """Chat with the AI.
    Gets user message,
    returns AI response,
    updates session topic,
    triggers refresh of list of puzzles and visualization
    """
    TOOL = "chat_routers:"
    print(f"{TOOL} chat_data from chat.html: ", chat_data)
    services = SessionService(db)
    triggers = [] # checks for new puzzle or session to update sidebar and visualization

    # get or create new session (get id, create topic name, store in database)
    session_id = await services.get_or_create_session(
        session_id=chat_data.session_id,
        user_message=chat_data.content,
        model=chat_data.model,
    )

     # Initialize agent
    agent = ChatAgent(db, session_id=str(session_id), model=chat_data.model)

    # Process message through agent and get response message
    llm_response, current_puzzle_id = await agent.process(chat_data.content)
    if llm_response:
        print(f"{TOOL} Received response from agent graph and pass it to database")

    # check for puzzle updates and update visualization to trigger HTMX
    topic_changed = False
    if current_puzzle_id:
        print(f"{TOOL} Current puzzle id: ", current_puzzle_id)
        triggers.append("refreshPuzzle")
        print(f"{TOOL} refresh puzzle editor")
        topic_changed = await services.update_session_title(
            puzzle_id=current_puzzle_id,
            session_id=session_id,
        )

    # If a new session is created refresh sidebar to add new session to list of sessions
    is_new_session = not chat_data.session_id or str(chat_data.session_id).strip() == "" # means: new session was just created
    print(f"{TOOL} is_new_session: ", is_new_session)
    if topic_changed or is_new_session:
        triggers.append("refreshSidebar")
        print(f"{TOOL} refresh sidebar")
    else:
        print(f"{TOOL} No new session")


    # fire the events (HTMX)
    print(f"{TOOL} fire triggers: ", triggers)
    response.headers["HX-Trigger"] = ", ".join(triggers)

    # format llm response to proper html output
    print(f"{TOOL} Format the LLM response into a readable HTML format")
    llm_response_html = markdown.markdown(llm_response)

    # create and send HTML response
    print(f"{TOOL} Pass content to front-end...")
    user_msg = f'<div class="user_message"><strong>You:</strong> {chat_data.content}</div>'
    ai_msg = f'<div class="ai_response"><strong>Rudolfo:</strong> {llm_response_html}</div>'

    # Update session_id in the hidden input
    session_script = f'<script>document.getElementById("session_id_input").value = "{session_id}";</script>'
    
    return HTMLResponse(content=user_msg + ai_msg + session_script)

# delete session
@router.delete("/chat/{session_id}/delete", response_class=HTMLResponse)
async def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """Delete chat by session id"""
    print("delete: session id from chat.html: ", session_id)
    services = SessionService(db)
    services.delete_session(session_id)
    return HTMLResponse(content="", status_code=200)

