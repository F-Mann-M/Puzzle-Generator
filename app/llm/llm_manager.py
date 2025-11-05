form app.llm.openai_client import OpenAIClient
from app.llm.google_client import GoogleClient

def get_llm(model_name: str):

    if model_name.startswith("gpt"):
        return OpenAIClient(model_name)
    elif model_name.startswith("gemini"):
        return GoogleClient(model_name)