from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

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
    latest_chat, latest_session_id = services.get_latest_session()
    print("show chat: ", latest_session_id)
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "latest_chat": latest_chat,
            "latest_session_id": latest_session_id
        }
    )


# Chat:
@router.post("/chat", response_class=HTMLResponse)
async def chat(
    chat_data: ChatFromRequest = Body(...),  # Explicitly parse from JSON body
    db: Session = Depends(get_db)
):
    """Chat with the AI"""
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