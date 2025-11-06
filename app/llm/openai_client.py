from app.core.config import settings
from openai import AsyncOpenAI

from app.schemas.puzzle_schema import PuzzleLLMResponse

API_KEY = settings.OPENAI_API_KEY

class OpenAIClient:
    def __init__(self, model_name="gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=API_KEY)
        self.model_name = model_name

    async def generate(self, messages: list):
        print("Thinking...")

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except TypeError:
            response = await self.client.chat.completions.create(model=self.model_name, messages=messages)


        content = response.choices[0].message.content
        print("Raw JSON:\n", content)

        # ---------- VALIDATION ----------
        # try:
        #     puzzle = PuzzleLLMResponse.model_validate_json(content)
        #     print("\n Parsed Puzzle:")
        #     print(puzzle.model_dump(indent=2))
        # except Exception as e:
        #     print("\n Validation failed:", e)

        # ---------- TOKEN USAGE ----------
        if response.usage:
            usage = response.usage
            print(
                f"\nTokens — prompt: {usage.prompt_tokens}, "
                f"completion: {usage.completion_tokens}, "
                f"total: {usage.total_tokens}"
            )

        return content
