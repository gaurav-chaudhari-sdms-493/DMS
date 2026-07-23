import logging
from openai import AsyncOpenAI
from typing import List, Union
from app.ai.base import LLMProvider, Message

logger = logging.getLogger(__name__)

class GroqLLMProvider(LLMProvider):
    def __init__(self, api_key: Union[str, List[str]], model: str):
        if isinstance(api_key, str):
            self.api_keys = [k.strip() for k in api_key.split(",") if k.strip()]
        else:
            self.api_keys = [k.strip() for k in api_key if k and k.strip()]
        
        if not self.api_keys:
            raise ValueError("No valid Groq API keys provided.")

        self.model = model
        self._current_index = 0

    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        attempts = 0
        max_attempts = len(self.api_keys)
        last_exception = None

        while attempts < max_attempts:
            current_key = self.api_keys[self._current_index]
            try:
                client = AsyncOpenAI(
                    api_key=current_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=formatted, # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Groq API Key (index {self._current_index}, key ending ...{current_key[-6:]}) failed: {e}. "
                    f"Rotating to next key..."
                )
                self._current_index = (self._current_index + 1) % len(self.api_keys)
                attempts += 1

        logger.error(f"All {max_attempts} Groq API key(s) failed or hit rate limits.")
        if last_exception:
            raise last_exception
        raise RuntimeError("All Groq API keys failed.")

