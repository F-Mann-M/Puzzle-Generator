from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from uuid import UUID

from app.core.database import get_db
from app.schemas import ChatFromRequest
from app.services import SessionService

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()


# load chat
@router.get("/chat", response_class=HTMLResponse)
async def show_chat(request: Request, db: Session = Depends(get_db)):
    """Get chat page and load latest session"""
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
            message_html += f'<div class="ai_response"><strong>Rudolfo:</strong> {message.content}</div>'

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

    # get llm response
    llm_response = await services.get_llm_response(chat_data.content, chat_data.model)

    # store user message and ai response to database
    await services.add_message(session_id, "User", chat_data.content)
    await services.add_message(session_id, "Rudolfo", llm_response)

    # create and send HTML response
    user_msg = f'<div class="user_message"><strong>You:</strong> {chat_data.content}</div>'
    ai_msg = f'<div class="ai_response"><strong>Rudolfo:</strong> {llm_response}</div>'
    return HTMLResponse(content=user_msg + ai_msg)


@router.delete("/chat/{session_id}")
async def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """Delete chat by session id"""
    services = SessionService(db)
    await services.delete_session(session_id)