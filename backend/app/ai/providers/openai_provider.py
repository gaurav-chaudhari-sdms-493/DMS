import asyncio
from openai import AsyncOpenAI
from typing import List
from app.ai.base import LLMProvider, EmbeddingProvider, Message
from app.services.config_service import get_int

class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        client = AsyncOpenAI(api_key=self.api_key)
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        response = await client.chat.completions.create(
            model=self.model,
            messages=formatted, # type: ignore
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dimensions: int):
        self.api_key = api_key
        self.model = model
        self._dimensions = dimensions

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # Handle empty text
        if not texts:
            return []
        
        client = AsyncOpenAI(api_key=self.api_key)
        # simple batching to avoid limit
        batch_size = await get_int("embed_api_batch_size", 100)
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await client.embeddings.create(
                input=batch,
                model=self.model,
                dimensions=self._dimensions
            )
            embeddings.extend([data.embedding for data in response.data])
        return embeddings

    @property
    def dimensions(self) -> int:
        return self._dimensions
