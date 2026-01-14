from google import genai
from app.core.config import settings
from app.schemas.puzzle_schema import PuzzleLLMResponse, PuzzleCreate
from pydantic import BaseModel
import logging
from utils.logger_config import configure_logging


logger = logging.getLogger(__name__)

API_KEY = settings.GEMINI_KEY

class GeminiClient:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.client = genai.Client(api_key=API_KEY)
        self.model_name = model_name

    def _get_clean_schema(self, pydantic_model: type[BaseModel]) -> dict:
        """
        Converts a Pydantic model to a Gemini-compatible JSON schema.
        Recursively removes 'additionalProperties' and 'title' fields.
        """
        schema = pydantic_model.model_json_schema()

        def clean_recursive(node):
            if isinstance(node, dict):
                # Remove forbidden keys
                node.pop("additionalProperties", None)
                node.pop("title", None)

                # Recurse into common schema keywords
                for key, value in node.items():
                    clean_recursive(value)

            elif isinstance(node, list):
                for item in node:
                    clean_recursive(item)

        clean_recursive(schema)
        return schema


    async def structured(self, prompt: str, schema: type[BaseModel]):
        """
        Takes in prompt and schema class.
        Note: For PuzzleLLMResponse, we force the raw schema to fix the bug.
        """
        # If the requested schema is PuzzleLLMResponse, use the raw dict to avoid error
        target_schema = self._get_clean_schema(schema)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt["user_prompt"],
                config={
                    "system_instruction": prompt["system_prompt"],
                    "response_mime_type": "application/json",
                    "response_schema": target_schema,
                },
            )
            logger.info(response.text)

            if response.parsed and isinstance(response.parsed, (dict, list)):
                return schema.model_validate(response.parsed)

            return response.parsed

        except Exception as e:
            logger.error(f"GeminiClient Structured Error: {e}", exc_info=True)
            return None



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
            logger.error(e)
            return None

        logger.info(response)

        return response.text
