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
        """ Generates puzzle (structured output)"""
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
        print("Raw JSON:\n", content) # Debugging

        puzzle = None

        # ---------- VALIDATION ----------
        try:
            puzzle = PuzzleLLMResponse.model_validate_json(content)
            print("\n Parsed Puzzle:") # Debugging
            print(puzzle)
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
