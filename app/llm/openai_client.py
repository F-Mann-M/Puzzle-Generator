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


        print("Token input: ", response.output[0].usage.total_input)
        print("Token output: ", response.output[0].usage.total_output)
        print("Token usage total: ", response.output[0].usage.total_tokens)
        return response.output[0].content[0].text


# Example Output for response
"""
Response(
    id='resp_0fd2ecd56dbac0300069242116b42081949db7f129c7089b6c', 
    created_at=1763975446.0, 
    error=None, 
    incomplete_details=None, 
    instructions=None, 
    metadata={}, 
    model='gpt-4o-mini-2024-07-18', 
    object='response', 
    output=[
        ResponseOutputMessage(
            id='msg_0fd2ecd56dbac03000692421175d5c8194b49675e26b14a747', 
            content=[
                ResponseOutputText(
                    annotations=[], 
                    text='Greetings, My Lord. How may I serve thee on this fine day?', 
                    type='output_text',
                    logprobs=[])], 
                    role='assistant', 
                    status='completed', 
                    type='message')
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
            reasoning=Reasoning(effort=None, 
            generate_summary=None, summary=None), 
            safety_identifier=None, 
            service_tier='default', 
            status='completed', 
            text=ResponseTextConfig(format=ResponseFormatText(type='text'), 
            verbosity='medium'), 
            top_logprobs=0, 
            truncation='disabled', 
            usage=ResponseUsage(
                input_tokens=1120, 
                input_tokens_details=InputTokensDetails(cached_tokens=0), 
                output_tokens=16, 
                output_tokens_details=OutputTokensDetails(reasoning_tokens=0), 
                total_tokens=1136), 
            user=None, 
            billing={'payer': 'developer'}, 
            prompt_cache_retention=None, 
            store=True)
"""
