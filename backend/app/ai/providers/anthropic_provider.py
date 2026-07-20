from anthropic import AsyncAnthropic
from typing import List
from app.ai.base import LLMProvider, Message

class AnthropicLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        system = ""
        user_messages = []
        for m in messages:
            if m.role == "system":
                system += m.content + "\n"
            else:
                user_messages.append({"role": m.role, "content": m.content})
                
        response = await self.client.messages.create(
            model=self.model,
            system=system,
            messages=user_messages, # type: ignore
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.content[0].text
