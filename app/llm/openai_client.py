from pydantic import BaseModel
from app.core.config import settings
from openai import AsyncOpenAI
from typing import Type, Any
import json
import logging

logger = logging.getLogger(__name__)

API_KEY = settings.OPENAI_API_KEY


class OpenAIClient:
    def __init__(self, model_name="gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=API_KEY)
        self.model_name = model_name

    def _clean_data(self, data: Any, schema: Type[BaseModel]) -> Any:
        """
        Removes fields from 'data' that are not defined in the Pydantic 'schema'.
        This prevents 'Extra inputs are not permitted' errors when extra='forbid' is used.
        """
        if not isinstance(data, dict):
            return data

        # Get the list of valid field names from the schema
        valid_keys = schema.model_fields.keys()

        # Create a new dict with ONLY the valid keys
        clean_data = {k: v for k, v in data.items() if k in valid_keys}

        return clean_data


    # Chat Function
    async def chat(self, prompt: dict):
        try:
            response = await self.client.responses.create(
                model=self.model_name,
                input=[
                    {"role": "system", "content": prompt.get("system_prompt")},
                    {"role": "user", "content": prompt.get("user_prompt")},
                ]
            )
        except TypeError:
            response = await self.client.responses.create(model=self.model_name, messages=prompt, stream=True)

        # ---------- TOKEN USAGE ----------
        logger.info("input tokens: ", response.usage.input_tokens)
        logger.info("output tokens: ", response.usage.output_tokens)
        logger.info("total tokens: ", response.usage.total_tokens)
        usage = [response.usage.input_tokens,response.usage.output_tokens, response.usage.total_tokens]

        return response.output[0].content[0].text



    # for structured output
    async def structured(self, prompt: dict, schema: type[BaseModel]):
        """ Generates puzzle (structured output)"""
        logger.info("openai_client: Thinking...")
        

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
        print("openai_client: Raw JSON:\n", content) # Debugging

        puzzle = None

        # ---------- VALIDATION ----------
        try:
            # 1. Parse JSON string to Dict
            raw_data = json.loads(content)

            # 2. Remove forbidden fields based on the dynamic schema passed in
            clean_data = self._clean_data(raw_data, schema)

            # 3. Validate
            puzzle = schema.model_validate(clean_data)

            logger.info("\n Parsed Puzzle successfully")
        except Exception as e:
            logger.error("\n Validation failed:", e)

        # ---------- TOKEN USAGE ----------
        if response.usage:
            usage = response.usage
            logger.info(
                "\n\n\n TOKEN USAGE"
                f"\nTokens — prompt: {usage.prompt_tokens}, "
                f"\ncompletion: {usage.completion_tokens}, "
                f"\ntotal: {usage.total_tokens}"
            )

        return puzzle