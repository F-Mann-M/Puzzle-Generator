from google import genai
from app.core.config import settings
from app.schemas.puzzle_schema import PuzzleLLMResponse, PuzzleCreate
from pydantic import BaseModel

API_KEY = settings.GEMINI_KEY


class GeminiClient:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.client = genai.Client(api_key=API_KEY)
        self.model_name = model_name

    async def generate(self, prompt: str):
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt["user_prompt"],
            config={
                "system_instruction": prompt["system_prompt"],
                "response_mime_type": "application/json",
                "response_schema": PuzzleLLMResponse,
            },
        )
        # Use the response as a JSON string.
        print(response.text)

        generated_puzzle = response.parsed
        return generated_puzzle


    async def structured(self, prompt: str, schema: type[BaseModel]):
        """Takes in prompt and schema class to generate structured output"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt["user_prompt"],
            config={
                "system_instruction": prompt["system_prompt"],
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
        # Use the response as a JSON string.
        print(response.text)

        generated_puzzle = response.parsed
        return generated_puzzle



    # Chat function
    async def chat(self, prompt: str):
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt["user_prompt"],
                config={
                    "system_instruction": prompt["system_prompt"],
                },
            )
        except Exception as e:
            print(e)
            return None

        print(response)

        return response.text
