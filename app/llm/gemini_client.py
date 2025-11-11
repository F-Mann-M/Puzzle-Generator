from google import genai
from app.core.config import settings
from app.schemas.puzzle_schema import PuzzleLLMResponse

API_KEY = settings.GEMINI_KEY


class GeminiClient:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.client = genai.Client(api_key=API_KEY)
        self.model_name = model_name

    async def generate(self, prompt: str):
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
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
