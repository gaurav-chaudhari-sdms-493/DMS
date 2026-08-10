from app.config import settings
from app.ai.base import LLMProvider, EmbeddingProvider, RerankerProvider, Message
from typing import List

import logging

logger = logging.getLogger(__name__)

_llm_provider: LLMProvider | None = None
_embed_provider: EmbeddingProvider | None = None
_rerank_provider: RerankerProvider | None = None

class FallbackEmbeddingProvider(EmbeddingProvider):
    def __init__(self, primary: EmbeddingProvider, fallback: EmbeddingProvider):
        self.primary = primary
        self.fallback = fallback

    async def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            return await self.primary.embed(texts)
        except Exception as e:
            logger.warning(f"Primary embedding provider ({self.primary.__class__.__name__}) failed: {e}. Falling back to secondary ({self.fallback.__class__.__name__}).")
            return await self.fallback.embed(texts)

    @property
    def dimensions(self) -> int:
        return self.primary.dimensions

class FallbackLLMProvider(LLMProvider):
    def __init__(self, primary: LLMProvider, secondary: LLMProvider | None = None):
        self.primary = primary
        self.secondary = secondary

    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        try:
            return await self.primary.complete(messages, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Primary LLM provider ({self.primary.__class__.__name__}) failed: {e}.")
            if self.secondary:
                try:
                    logger.info(f"Attempting fallback LLM provider ({self.secondary.__class__.__name__}).")
                    return await self.secondary.complete(messages, temperature, max_tokens)
                except Exception as inner_e:
                    logger.warning(f"Secondary LLM provider ({self.secondary.__class__.__name__}) failed: {inner_e}.")
                    raise inner_e
            raise e

def get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is not None:
        return _llm_provider

    primary: LLMProvider | None = None
    secondary: LLMProvider | None = None

    if settings.ai_llm_provider == 'groq':
        from app.ai.providers.groq_provider import GroqLLMProvider
        groq_keys = settings.get_groq_api_keys()
        primary = GroqLLMProvider(api_key=groq_keys if groq_keys else settings.groq_api_key, model=settings.groq_llm_model)
        if settings.openai_api_key:
            from app.ai.providers.openai_provider import OpenAILLMProvider
            secondary = OpenAILLMProvider(api_key=settings.openai_api_key, model=settings.openai_llm_model)
    elif settings.ai_llm_provider == 'openai':
        from app.ai.providers.openai_provider import OpenAILLMProvider
        primary = OpenAILLMProvider(api_key=settings.openai_api_key, model=settings.openai_llm_model)
        groq_keys = settings.get_groq_api_keys()
        if groq_keys or settings.groq_api_key:
            from app.ai.providers.groq_provider import GroqLLMProvider
            secondary = GroqLLMProvider(api_key=groq_keys if groq_keys else settings.groq_api_key, model=settings.groq_llm_model)
    elif settings.ai_llm_provider == 'anthropic':
        from app.ai.providers.anthropic_provider import AnthropicLLMProvider
        primary = AnthropicLLMProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_llm_model)
    else:
        raise ValueError(f'Unknown LLM provider: {settings.ai_llm_provider}')

    _llm_provider = FallbackLLMProvider(primary, secondary)
    return _llm_provider


def get_embed_provider() -> EmbeddingProvider:
    global _embed_provider
    if _embed_provider is not None:
        return _embed_provider

    primary_provider = None
    if settings.ai_embed_provider == 'openai':
        from app.ai.providers.openai_provider import OpenAIEmbeddingProvider
        primary_provider = OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key, 
            model=settings.openai_embed_model, 
            dimensions=settings.openai_embed_dimensions
        )
    elif settings.ai_embed_provider == 'bgem3':
        from app.ai.providers.bgem3_provider import BGEM3EmbeddingProvider
        primary_provider = BGEM3EmbeddingProvider()
    elif settings.ai_embed_provider == 'gemini':
        from app.ai.providers.gemini_provider import GeminiEmbeddingProvider
        primary_provider = GeminiEmbeddingProvider(api_key=settings.google_api_key, model=settings.gemini_embed_model)
    elif settings.ai_embed_provider == 'cohere':
        from app.ai.providers.cohere_provider import CohereEmbeddingProvider
        primary_provider = CohereEmbeddingProvider(api_key=settings.cohere_api_key, model="embed-english-v3.0")
    else:
        raise ValueError(f'Unknown Embedding provider: {settings.ai_embed_provider}')

    fallback_provider = None
    if settings.ai_embed_fallback_provider == 'cohere':
        from app.ai.providers.cohere_provider import CohereEmbeddingProvider
        fallback_provider = CohereEmbeddingProvider(api_key=settings.cohere_api_key, model="embed-english-v3.0")
    elif settings.ai_embed_fallback_provider == 'openai':
        from app.ai.providers.openai_provider import OpenAIEmbeddingProvider
        fallback_provider = OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embed_model,
            dimensions=settings.openai_embed_dimensions
        )

    if fallback_provider:
        _embed_provider = FallbackEmbeddingProvider(primary_provider, fallback_provider)
    else:
        _embed_provider = primary_provider

    return _embed_provider


def get_rerank_provider() -> RerankerProvider:
    global _rerank_provider
    if _rerank_provider is not None:
        return _rerank_provider

    if settings.ai_rerank_provider == 'cohere':
        from app.ai.providers.cohere_provider import CohereRerankerProvider
        _rerank_provider = CohereRerankerProvider(api_key=settings.cohere_api_key, model=settings.cohere_rerank_model)
    else:
        class DummyReranker(RerankerProvider):
            async def rerank(self, query: str, documents: list[str], top_n: int = 5):
                from app.ai.base import RankedResult
                return [RankedResult(index=i, score=1.0, text=d) for i, d in enumerate(documents[:top_n])]
        _rerank_provider = DummyReranker()

    return _rerank_provider
