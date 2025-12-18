from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings): # load all key=value pairs from .env
    """ Load Keys"""
    CHECKPOINTS_URL: str = f"{BASE_DIR / 'data' /'checkpoints.sqlite'}"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'puzzle.db'}"
    OPENAI_KEY: str
    GEMINI_KEY: str
    GROQ_API_KEY: str
    CLAUD_KEY: str
    OPENAI_API_KEY: str # Masterschool key
    TAVILY_API_KEY: str # Websearch API for tutorial

    model_config = SettingsConfigDict(
        env_file = BASE_DIR/".env",
        env_file_encoding = "utf-8",
    )

settings = Settings()