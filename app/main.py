from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from app.routers import puzzle_routers
from app.database import Base, engine
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Create database tables
Base.metadata.create_all(bind=engine)

# create FastAPI
app = FastAPI(title="Puzzle Generator API", version="1.0")

# create Jinja2 template engine/define templates directory
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# get routers
app.include_router(puzzle_routers.router, prefix="/puzzles", tags=["Puzzles"])


# Landing page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})