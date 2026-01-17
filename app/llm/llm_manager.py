from app.llm.gemini_client import GeminiClient
from app.llm.openai_client import OpenAIClient
from app.core.config import settings

OPENAI_API_KEY = settings.OPENAI_API_KEY
GOOLGE_API_KEY = settings.GOOGLE_API_KEY

def get_llm(model_name: str):
    """ Select model based on name"""
    if model_name.startswith("gpt"):
        return OpenAIClient(model_name)
    elif model_name.startswith("gemini"):
        return GeminiClient(model_name)
