from openai import AsyncOpenAI
from typing import List
from app.ai.base import LLMProvider, Message

class GroqLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        response = await client.chat.completions.create(
            model=self.model,
            messages=formatted, # type: ignore
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""
