from app.config import settings
from app.ai.base import LLMProvider, EmbeddingProvider, RerankerProvider
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

def get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        if settings.ai_llm_provider == 'openai':
            from app.ai.providers.openai_provider import OpenAILLMProvider
            _llm_provider = OpenAILLMProvider(api_key=settings.openai_api_key, model=settings.openai_llm_model)
        elif settings.ai_llm_provider == 'anthropic':
            from app.ai.providers.anthropic_provider import AnthropicLLMProvider
            _llm_provider = AnthropicLLMProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_llm_model)
        elif settings.ai_llm_provider == 'groq':
            from app.ai.providers.groq_provider import GroqLLMProvider
            _llm_provider = GroqLLMProvider(api_key=settings.groq_api_key, model=settings.groq_llm_model)
        elif settings.ai_llm_provider == 'ollama':
            from app.ai.providers.ollama_provider import OllamaLLMProvider
            _llm_provider = OllamaLLMProvider(base_url=settings.ollama_base_url, model=settings.ollama_llm_model)
        elif settings.ai_llm_provider in ('local', 'dummy', 'none'):
            from app.ai.providers.local_provider import LocalLLMProvider
            _llm_provider = LocalLLMProvider()
        else:
            from app.ai.providers.local_provider import LocalLLMProvider
            _llm_provider = LocalLLMProvider()
    return _llm_provider

def get_embed_provider() -> EmbeddingProvider:
    global _embed_provider
    if _embed_provider is None:
        # Resolve primary embedding provider
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
        elif settings.ai_embed_provider == 'ollama':
            from app.ai.providers.ollama_provider import OllamaEmbeddingProvider
            primary_provider = OllamaEmbeddingProvider(base_url=settings.ollama_base_url, model=settings.ollama_embed_model)
        else:
            raise ValueError(f'Unknown Embedding provider: {settings.ai_embed_provider}')

        # Resolve fallback embedding provider if configured
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

        # Wrap in FallbackEmbeddingProvider if a fallback exists
        if fallback_provider:
            _embed_provider = FallbackEmbeddingProvider(primary_provider, fallback_provider)
        else:
            _embed_provider = primary_provider

    return _embed_provider

def get_rerank_provider() -> RerankerProvider:
    global _rerank_provider
    if _rerank_provider is None:
        if settings.ai_rerank_provider == 'cohere':
            from app.ai.providers.cohere_provider import CohereRerankerProvider
            _rerank_provider = CohereRerankerProvider(api_key=settings.cohere_api_key, model=settings.cohere_rerank_model)
        elif settings.ai_rerank_provider == 'bge':
            from app.ai.providers.bge_reranker_provider import BGERerankerProvider
            _rerank_provider = BGERerankerProvider(model_name=settings.local_rerank_model)
        else:
            class DummyReranker(RerankerProvider):
                async def rerank(self, query: str, documents: list[str], top_n: int = 5):
                    from app.ai.base import RankedResult
                    return [RankedResult(index=i, score=1.0, text=d) for i, d in enumerate(documents[:top_n])]
            _rerank_provider = DummyReranker()
    return _rerank_provider
