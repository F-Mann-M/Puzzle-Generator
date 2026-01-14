from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from app.routers import puzzle_routers, chat_routers
from app.core.database import Base, engine, SessionLocal, get_db
from app.services import SessionService
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
from utils.logger_config import configure_logging

# configurate logger
configure_logging()

# get logger
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")

    # Create DB tables
    Base.metadata.create_all(bind=engine)

    # Run Cleanup Task: Ensure all puzzles have sessions
    logger.info("Running startup cleanup: Ensuring puzzles have sessions and checkpointers have real sessions...")
    db = SessionLocal()
    try:
        session_service = SessionService(db)
        await session_service.ensure_puzzles_have_sessions()
        await session_service.ensure_checkpointer_have_sessions()
    except Exception as e:
        logger.error(f"Startup cleanup failed: {e}", exc_info=True)
    finally:
        db.close()

    yield

    logger.info("Application shutting down...")


# create FastAPI with lifespan
app = FastAPI(
    title="Puzzle Generator API",
    version="1.0",
    lifespan=lifespan  # <--- Register the lifespan handler here
)

# create Jinja2 template engine/define templates directory
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# get routers
app.include_router(chat_routers.router, prefix="/puzzles", tags=["Chat"])
app.include_router(puzzle_routers.router, prefix="/puzzles", tags=["Puzzles"])


# Landing page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})