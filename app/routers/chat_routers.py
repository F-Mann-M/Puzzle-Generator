from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from uuid import UUID
import markdown

from app.core.database import get_db
from app.schemas import ChatFromRequest
from app.services import SessionService
from app.agents import ChatAgent
from app import models

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()


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
async def get_session(session_id: UUID, db: Session = Depends(get_db)):
    """Get chat history by session id"""
    print("session id from chat.html: ", session_id)

    services = SessionService(db)
    session_messages = services.get_session_messages(session_id)

    if not session_messages:
        return HTMLResponse(content="Session has no content yet.")

    message_html = ""
    for message in session_messages:
        if message.role == "User":
            message_html += f'<div class="user_message"><strong>You:</strong> {message.content}</div>'
        else:
            message_content = markdown.markdown(message.content)
            message_html += f'<div class="ai_response"><strong>Rudolfo:</strong> {message_content}</div>'

    return HTMLResponse(content=message_html)


# Chat:
@router.post("/chat", response_class=HTMLResponse)
async def chat(
    chat_data: ChatFromRequest = Body(...),  # parse from JSON body
    db: Session = Depends(get_db)
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

    # # Get chat history for chat agent
    # print("get session messages: ", session_id)
    # chat_messages = services.get_session_messages(session_id)
    # chat_history = [
    #     {"role": msg.role, "content": msg.content}
    #     for msg in chat_messages[-10:]
    # ]

    # Initialize agent
    agent = ChatAgent(db, session_id, chat_data.model)

    # Process message through agent
    llm_response = await agent.process(chat_data.content)
    if llm_response:
        print("Received response from agent graph and pass it to database")


    # store user message and ai response to database
    await services.add_message(session_id, "User", chat_data.content)
    await services.add_message(session_id, "Rudolfo", llm_response)

    # format llm response to proper html output
    print("Format the LLM response into a readable HTML format")
    llm_response_html = markdown.markdown(llm_response)

    # create and send HTML response
    print("Pass content to front-end...")
    user_msg = f'<div class="user_message"><strong>You:</strong> {chat_data.content}</div>'
    ai_msg = f'<div class="ai_response"><strong>Rudolfo:</strong> {llm_response_html}</div>'
    return HTMLResponse(content=user_msg + ai_msg)


@router.delete("/chat/{session_id}/delete", response_class=HTMLResponse)
async def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """Delete chat by session id"""
    print("delete: session id from chat.html: ", session_id)
    services = SessionService(db)
    services.delete_session(session_id)
    return HTMLResponse(content="", status_code=200)


@router.get("/chat/{session_id}/puzzle", response_class=HTMLResponse)
async def get_puzzle(session_id: UUID, db: Session = Depends(get_db)):
    """Get puzzle id via session id"""
    services = SessionService(db)
    session = db.query(models.Session).filter(models.Session.id == session_id).first()

    if not session:
        return HTMLResponse(content="<div>Session not found.</div>")

    puzzle_id = session.puzzle_id
    print("puzzle_id: ", puzzle_id)

    if not puzzle_id:
        return HTMLResponse(content="<div>No puzzle yet.</div>")

    return HTMLResponse(
        content=f'<svg id="puzzle-visualization-svg" data-puzzle-id="{puzzle_id}" style="width: 100%; height: 100%;"></svg>'
    )