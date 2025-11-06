from app.core.config import settings
from openai import OpenAI
from app.schemas.puzzle_schema import PuzzleLLMResponse

API_KEY = settings.OPENAI_API_KEY

class OpenAIClient:
    def __init__(self, model_name="gpt-4o-mini"):
        self.client = OpenAI(api_key=API_KEY)
        self.model_name = model_name

    async def generate(self, prompt: str):
        response = self.client.responses.parse(
            model=self.model_name,
            input=[
                {
                    "role": "developer",
                    "content": "you are a support agent. Return ONLY the json object.",
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=1,
            text_format=PuzzleLLMResponse,
            max_output_tokens=1000,
        )

        puzzle = response.output_parsed
        return puzzle
