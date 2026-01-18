from fastapi import APIRouter, Depends, Request, Body, Response, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from uuid import UUID
import markdown
from typing import Optional
import logging
import re # to convert LLM formated text

from app import models
from app.core.database import get_db
from app.schemas import ChatFromRequest
from app.services import SessionService, PuzzleServices
from app.agents import ChatAgent

logger = logging.getLogger(__name__)

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
        logger.info("no session id yet")
        return templates.TemplateResponse(
            "partials/editor_partial.html",
            {
                "request": request,
                "puzzle": None,
            }
        )

    try:
        # manual conversion
        session_uuid = UUID(session_id.strip())
    except (ValueError, TypeError):
        return templates.TemplateResponse(
            "partials/editor_partial.html",
            {
                "request": request,
                "puzzle": None,
            }
        )

    session_services = SessionService(db)
    puzzle_id = session_services.get_puzzle_id(session_uuid)

    if not puzzle_id:
        return templates.TemplateResponse(
            "partials/editor_partial.html",
            {
                "request": request,
                "puzzle": None,
            }
        )

    puzzle_services = PuzzleServices(db)
    puzzle = puzzle_services.get_puzzle_by_id(puzzle_id)

    return templates.TemplateResponse(
        "partials/editor_partial.html",
        {
            "request": request,
            "puzzle": puzzle,
        }
    )


@router.get("/chat/puzzle/{puzzle_id}", response_class=HTMLResponse)
async def get_chat(puzzle_id: UUID, db: Session = Depends(get_db), request: Request = None):
    """Loads Chat from Puzzle"""
    logger.info(f"Loading Chat from Puzzle list: {puzzle_id}")

    try:
        session = db.query(models.Session).filter(models.Session.puzzle_id == puzzle_id).first()
    except Exception as e:
        logger.error(f"Error getting Chat from Puzzle: {e}")
        session = None

    services = SessionService(db)
    all_sessions = services.get_all_sessions()
    
    latest_session_id = None
    if session:
        latest_session_id = session.id
    else:
        logger.debug(f"No session for Puzzle {puzzle_id}")
    
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "all_sessions": all_sessions,
            "latest_session_id": latest_session_id,
        }
    )



# load chat
@router.get("/chat", response_class=HTMLResponse)
async def show_chat(request: Request, db: Session = Depends(get_db)):
    """Get chat page and load all sessions."""
    services = SessionService(db)
    all_sessions = services.get_all_sessions()

    if all_sessions:
        lastest_session = services.get_latest_session()
    else:
        lastest_session = None
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

    logger.info("reload all sessions...")
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
async def get_session(session_id: UUID, db: Session = Depends(get_db), response: Response = Response()):
    """Get chat history by session id """
    logger.debug("session id from chat.html: ", session_id)

    # Initialize ChatAgent
    agent = ChatAgent(db, str(session_id), "gpt-4o-mini") # Use gpt-40-mini as default value

    # Load states from LangGraph checkpointer
    state_history = await agent.get_history()

    if not state_history:
        # Even if no history, trigger refreshPuzzle to update editor
        html_response = HTMLResponse(content="Session has no content yet.")
        html_response.headers["HX-Trigger"] = "refreshPuzzle"
        return html_response

    message_html = ""
    for message in state_history:
        # Access by key because LangGraph history uses dicts or message objects
        role = message.get("role") if isinstance(message, dict) else message.type
        content = message.get("content") if isinstance(message, dict) else message.content

        if role == "user":
            message_html += f'<div class="user_message">{content}</div>'
        else:
            corrected_text = re.sub(r'^[ \t]{1,3}-', '    -', content, flags=re.MULTILINE)
            message_content = markdown.markdown(corrected_text, extensions=['extra', 'sane_lists'])
            message_html += f'<div class="ai_response">{message_content}</div>'

    # Trigger refreshPuzzle to update editor when session is loaded
    html_response = HTMLResponse(content=message_html)
    html_response.headers["HX-Trigger"] = "refreshPuzzle"
    
    return html_response


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
    logger.info(f"\n\nchat_data from chat.html: {chat_data}")
    services = SessionService(db)

    # Check if new session started
    is_new_session = not chat_data.session_id or str(chat_data.session_id).strip() == ""

    # get or create new session (get id, create topic name, store in database)
    session_id = await services.get_or_create_session(
        session_id=chat_data.session_id,
        user_message=chat_data.content,
        model=chat_data.model,
    )

    # check if current session has a puzzle and puzzle context
    puzzle_id = services.get_puzzle_id(session_id=session_id)
    if not puzzle_id:
        logger.debug(f"No puzzle found for session id '{session_id}'")
    puzzle_json = None
    if session_id and puzzle_id:
        puzzle_json = await services.get_serialized_puzzle_json(
            session_id=session_id,
            model=chat_data.model)
        if puzzle_json:
            logger.debug(f"Puzzle JSON loaded ({len(str(puzzle_json))} chars)")
        else:
            logger.warning(f"Puzzle JSON is EMPTY for Session {session_id} / Puzzle {puzzle_id}")

     # Initialize agent
    agent = ChatAgent(db, session_id=str(session_id), model=chat_data.model)

    async def response_generator():
        # UI update
        # Yield user message

        # if it's a new session update hidden input on chat.html 'session_id_input'

        # Yield AI Message

        # Stream Agend reasoning

        # close html div (bubble)
        pass




    # # Process message through agent and get response message
    # llm_response, current_puzzle_id = await agent.process(
    #     user_message=chat_data.content,
    #     puzzle_json=puzzle_json,
    #     puzzle_id=puzzle_id,
    # )
    #
    #
    # if llm_response:
    #     logger.debug(f"Received response from agent graph and pass it to database")
    #
    # # check for puzzle updates and update visualization to trigger HTMX
    # topic_changed = False
    # if current_puzzle_id:
    #     logger.debug(f"Current puzzle id: ", current_puzzle_id)
    #     triggers.append("refreshPuzzle")
    #     logger.debug(f"refresh puzzle editor")
    #     topic_changed = await services.update_session_title(
    #         puzzle_id=current_puzzle_id,
    #         session_id=session_id,
    #     )
    #
    # # If a new session is created refresh sidebar to add new session to list of sessions
    # is_new_session = not chat_data.session_id or str(chat_data.session_id).strip() == "" # means: new session was just created
    # logger.debug(f"is_new_session: ", is_new_session)
    # if topic_changed or is_new_session:
    #     triggers.append("refreshSidebar")
    #     logger.debug(f"efresh sidebar")
    # else:
    #     logger.debug(f"No new session")
    #
    #
    # # fire the events (HTMX)
    # logger.debug(f"fire triggers: ", triggers)
    # response.headers["HX-Trigger"] = ", ".join(triggers)
    #
    # # format llm response to proper html output
    # logger.debug(f"Format the LLM response into a readable HTML format")
    # corrected_text = re.sub(r'^[ \t]{1,3}-', '    -', llm_response, flags=re.MULTILINE)
    # llm_response_html = markdown.markdown(corrected_text, extensions=['extra', 'sane_lists'])
    #
    # # create and send HTML response
    # logger.debug(f"ass content to front-end...")
    # user_msg = f'<div class="user_message">{chat_data.content}</div>'
    # ai_msg = f'<div class="ai_response">{llm_response_html}</div>'
    #
    # # Update session_id in the hidden input
    # session_script = f'<script>document.getElementById("session_id_input").value = "{session_id}";</script>'
    #
    # html_response = HTMLResponse(content=user_msg + ai_msg + session_script)
    # html_response.headers["HX-Trigger"] = "refreshPuzzle"
    # return html_response


# delete session
@router.delete("/chat/{session_id}/delete", response_class=HTMLResponse)
async def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """Delete session, related puzzle and LangGraph memory by session id"""
    logger.debug("delete: session id from chat.html: ", session_id)
    session_services = SessionService(db)

    await session_services.delete_session(session_id)
    html_response = HTMLResponse(content="", status_code=200)
    html_response.headers["HX-Trigger"] = "refreshSidebar, refreshPuzzle, clearChat"

    return html_response

