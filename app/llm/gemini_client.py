from google import genai
from app.core.config import settings
from app.schemas.puzzle_schema import PuzzleLLMResponse, PuzzleCreate
from pydantic import BaseModel

API_KEY = settings.GEMINI_KEY

# # Manually defined schema to avoid SDK "additional_properties" bug
# PUZZLE_SCHEMA = {
#     "type": "OBJECT",
#     "properties": {
#         "nodes": {
#             "type": "ARRAY",
#             "items": {
#                 "type": "OBJECT",
#                 "properties": {
#                     "index": {"type": "INTEGER"},
#                     "x": {"type": "INTEGER"},
#                     "y": {"type": "INTEGER"}
#                 },
#                 "required": ["index", "x", "y"]
#             }
#         },
#         "edges": {
#             "type": "ARRAY",
#             "items": {
#                 "type": "OBJECT",
#                 "properties": {
#                     "index": {"type": "INTEGER"},
#                     "start": {"type": "INTEGER"},
#                     "end": {"type": "INTEGER"}
#                 },
#                 "required": ["index", "start", "end"]
#             }
#         },
#         "units": {
#             "type": "ARRAY",
#             "items": {
#                 "type": "OBJECT",
#                 "properties": {
#                     "type": {"type": "STRING"},
#                     "faction": {"type": "STRING"},
#                     "path": {
#                         "type": "ARRAY",
#                         "items": {"type": "INTEGER"}
#                     }
#                 },
#                 "required": ["type", "faction", "path"]
#             }
#         },
#         "coins": {"type": "INTEGER", "nullable": True},
#         "description": {"type": "STRING", "nullable": True}
#     },
#     "required": ["nodes", "edges", "units"]
# }

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

    # async def generate(self, prompt: str):
    #     response = self.client.models.generate_content(
    #         model=self.model_name,
    #         contents=prompt["user_prompt"],
    #         config={
    #             "system_instruction": prompt["system_prompt"],
    #             "response_mime_type": "application/json",
    #             "response_schema": PuzzleLLMResponse,
    #         },
    #     )
    #     # Use the response as a JSON string.
    #     print(response.text)
    #
    #     if response.parsed and isinstance(response.parsed, (dict, list)):
    #         return PuzzleLLMResponse.model_validate(response.parsed)
    #
    #     generated_puzzle = response.parsed
    #     return generated_puzzle


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
            print(response.text)

            if response.parsed and isinstance(response.parsed, (dict, list)):
                return schema.model_validate(response.parsed)

            return response.parsed

        except Exception as e:
            print(f"GeminiClient Structured Error: {e}")
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
            print(e)
            return None

        print(response)

        return response.text
