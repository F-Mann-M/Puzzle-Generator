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
from app import models

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()

# load puzzle id for visualization
@router.get("/chat/visualize", response_class=HTMLResponse)
async def get_puzzle_by_session_id(session_id: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    """Get current puzzle id via session_id"""

    print("get puzzle: session id from chat.html: ", session_id)

    # Handle empty string
    if not session_id or session_id.strip() == "" or session_id is None:
        return HTMLResponse(content="<div>Select a session to view the puzzle.</div>")


    try:
        # convert session id manually
        session_uuid = UUID(session_id.strip())
    except (ValueError, TypeError) as e:
        print(f"Invalid session id: {session_uuid}, error: {e}")
        return HTMLResponse(content=f"<div>Invalid session ID: {e}.</div>")


    # Fetch the puzzle from your database/service
    session_services = SessionService(db)
    current_puzzle_id = await session_services.get_puzzle_id(session_uuid)
    print("Get puzzle id for visualization: ", current_puzzle_id)

    # If no puzzle is found, return a placeholder
    if not current_puzzle_id:
        return HTMLResponse(content="<div>No puzzle yet.</div>")

    try:
        # Fetch puzzle
        puzzle_services = PuzzleServices(db)
        puzzle = puzzle_services.get_puzzle_by_id(current_puzzle_id)
    except Exception as e:
        print(f"Error feching puzzle {e}")
        return HTMLResponse(content="<div>No puzzle yet.</div>")

    # Return the HTML/SVG string
    print("return puzzle visualization")
    return HTMLResponse(content=f'<strong>Name:</strong> {puzzle.name}<br>'
                                f'<strong>Game Mode:</strong> {puzzle.game_mode}<br>'
                                f'<svg id="puzzle-visualization-svg" data-puzzle-id="{current_puzzle_id}" style="width: 100%; min-height: 400px;"></svg>'
                                f"<strong>Description:</strong>{puzzle.description}<br>"
                        )

# load chat
@router.get("/chat", response_class=HTMLResponse)
async def show_chat(request: Request, db: Session = Depends(get_db)):
    """Get chat page and load all sessions."""
    services = SessionService(db)
    all_sessions = services.get_all_sessions()
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "all_sessions": all_sessions,
        }
    )

@router.get("/chat/{session_id}", response_class=HTMLResponse)
async def get_session(session_id: UUID, db: Session = Depends(get_db), response: Response = Response()):
    """Get chat history by session id"""
    print("session id from chat.html: ", session_id)

    services = SessionService(db)
    session_messages = services.get_session_messages(session_id)

    if not session_messages:
        return HTMLResponse(content="Session has no content yet.")

    message_html = ""
    for message in session_messages:
        if message.role == "user":
            message_html += f'<div class="user_message"><strong>You:</strong> {message.content}</div>'
        else:
            message_content = markdown.markdown(message.content)
            message_html += f'<div class="ai_response"><strong>Rudolfo:</strong> {message_content}</div>'

    return HTMLResponse(content=message_html)


# Chat:
@router.post("/chat", response_class=HTMLResponse)
async def chat(
    chat_data: ChatFromRequest = Body(...),  # parse from JSON body
    db: Session = Depends(get_db),
    response: Response = Response(), # visualize puzzle container ask for puzzle update
):
    """Chat with the AI. Gets user message, returns AI response"""
    print("chat_data from chat.html: ", chat_data)
    services = SessionService(db)

    # get or create new session (get id, create topic name, store in database)
    session_id = await services.get_or_create_session(
        session_id=chat_data.session_id,
        user_message=chat_data.content,
        model=chat_data.model,
    )

    # get puzzle id
    puzzle_id_from_session = await services.get_puzzle_id(session_id)
    if puzzle_id_from_session:
        print("Takes in puzzle id from session: ", puzzle_id_from_session)

    # Initialize agent
    agent = ChatAgent(db, session_id, chat_data.model)

    # Process message through agent and get response message
    llm_response, current_puzzle_id = await agent.process(chat_data.content, puzzle_id_from_session)
    if llm_response:
        print("Received response from agent graph and pass it to database")

    # check for puzzle updates and update visualization (HTMX)
    if current_puzzle_id:
        print("Current puzzle id (chat router): ", current_puzzle_id)
        # fire the event "refreshPuzzle" (HTMX)
        response.headers["HX-Trigger"] = "refreshPuzzle"
    else:
        print("No puzzle id yet")

    # store user message and LLM response to database
    await services.add_message(session_id, "user", chat_data.content)
    await services.add_message(session_id, "assistant", llm_response)

    # format llm response to proper html output
    print("Format the LLM response into a readable HTML format")
    llm_response_html = markdown.markdown(llm_response)


    # create and send HTML response
    print("Pass content to front-end...")
    user_msg = f'<div class="user_message"><strong>You:</strong> {chat_data.content}</div>'
    ai_msg = f'<div class="ai_response"><strong>Rudolfo:</strong> {llm_response_html}</div>'

    # Include session_id update script in the response
    # Update session_id in the hidden input
    session_script = f'<script>document.getElementById("session_id_input").value = "{session_id}";</script>'
    
    return HTMLResponse(content=user_msg + ai_msg + session_script)


@router.delete("/chat/{session_id}/delete", response_class=HTMLResponse)
async def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """Delete chat by session id"""
    print("delete: session id from chat.html: ", session_id)
    services = SessionService(db)
    services.delete_session(session_id)
    return HTMLResponse(content="", status_code=200)
