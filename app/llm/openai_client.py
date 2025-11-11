import json

from app.core.config import settings
from openai import AsyncOpenAI

from app.schemas.puzzle_schema import PuzzleLLMResponse

API_KEY = settings.OPENAI_API_KEY

class OpenAIClient:
    def __init__(self, model_name="gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=API_KEY)
        self.model_name = model_name

    async def generate(self, prompt: dict):
        print("Thinking...")
        print("system_prompt: ", prompt.get("system_prompt"))

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": prompt.get("system_prompt")},
                          {"role": "user", "content": prompt.get("user_prompt")}],
                response_format={"type": "json_object"},
            )
        except TypeError:
            response = await self.client.chat.completions.create(model=self.model_name, messages=prompt)


        content = response.choices[0].message.content
        print("Raw JSON:\n", content)


        puzzle = None

        # ---------- VALIDATION ----------
        try:
            puzzle = PuzzleLLMResponse.model_validate_json(content)
            print("\n Parsed Puzzle:")
            print(puzzle)
        except Exception as e:
            print("\n Validation failed:", e)

        # ---------- TOKEN USAGE ----------
        if response.usage:
            usage = response.usage
            print(
                f"\nTokens — prompt: {usage.prompt_tokens}, "
                f"completion: {usage.completion_tokens}, "
                f"total: {usage.total_tokens}"
            )

        return puzzle
