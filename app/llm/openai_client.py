from pydantic import BaseModel
from app.core.config import settings
from openai import AsyncOpenAI
from typing import Type, Any
import json


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
        print("input tokens: ", response.usage.input_tokens)
        print("output tokens: ", response.usage.output_tokens)
        print("total tokens: ", response.usage.total_tokens)
        usage = [response.usage.input_tokens,response.usage.output_tokens, response.usage.total_tokens]

        return response.output[0].content[0].text



    # for structured output
    async def structured(self, prompt: dict, schema: type[BaseModel]):
        """ Generates puzzle (structured output)"""
        print("openai_client: Thinking...")
        #print("system_prompt: ", prompt.get("system_prompt"))
        #print("openai_client: User Prompt: ", prompt.get("user_prompt"))

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

            print("\n Parsed Puzzle successfully")
        except Exception as e:
            print("\n Validation failed:", e)

        # ---------- TOKEN USAGE ----------
        if response.usage:
            usage = response.usage
            print(
                "\n\n\n TOKEN USAGE"
                f"\nTokens — prompt: {usage.prompt_tokens}, "
                f"\ncompletion: {usage.completion_tokens}, "
                f"\ntotal: {usage.total_tokens}"
            )

        return puzzle

# example output:
"""
Response(
id='resp_02ab2d717d67591d0069381ec39f00819792ec4b4c38399099', 
created_at=1765285571.0, 
error=None, 
incomplete_details=None, 
instructions=None, 
metadata={}, 
model='gpt-4o-mini-2024-07-18', 
object='response', 
output=[
    ResponseOutputMessage(
        id='msg_02ab2d717d67591d0069381ec4251881979b1a6bba86b1c1d2', 
        content=[
            ResponseOutputText(
                annotations=[], 
                text='Ah, noble Goetz, it seems you wish to test the waters once more. Pray, let me assist you in your quest or strife related to the puzzle at hand. Speak your desire!', 
                type='output_text', logprobs=[])], 
                role='assistant', 
                status='completed', 
                type='message'
                )
            ], 
        parallel_tool_calls=True, 
        temperature=1.0, 
        tool_choice='auto',
        tools=[], 
        top_p=1.0, 
        background=False, 
        conversation=None, 
        max_output_tokens=None, 
        max_tool_calls=None, 
        previous_response_id=None, 
        prompt=None, 
        prompt_cache_key=None, 
        prompt_cache_retention=None, 
        reasoning=Reasoning(
            effort=None, 
            generate_summary=None, 
            summary=None), 
            safety_identifier=None, 
            service_tier='default', 
            status='completed', 
            text=ResponseTextConfig(format=ResponseFormatText(type='text'), verbosity='medium'), 
        top_logprobs=0, 
        truncation='disabled', 
        usage=ResponseUsage(
            input_tokens=1185, 
            input_tokens_details=InputTokensDetails(cached_tokens=0), 
            output_tokens=41, 
            output_tokens_details=OutputTokensDetails(reasoning_tokens=0), 
            total_tokens=1226), 
        user=None, 
        billing={'payer': 'developer'}, store=True)
"""
