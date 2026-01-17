import logging

from app.llm.openai_client import OpenAIClient
from app.llm.gemini_client import GeminiClient

def get_llm(model_name: str):
    """ Select model based on name"""
    if model_name.startswith("gpt"):
        return OpenAIClient(model_name)
    elif model_name.startswith("gemini"):
        return GeminiClient(model_name)


# def get_lang_graph_llm(model_name: str):
#     """ Select model based on name"""
#     if model_name.startswith("gpt"):
#         return OpenAIClient(model_name)
#     elif model_name.startswith("gemini"):
#         return GeminiClient(model_name)