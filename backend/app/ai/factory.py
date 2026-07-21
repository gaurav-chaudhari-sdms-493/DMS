import logging
from app.config import settings
from app.ai.base import LLMProvider, EmbeddingProvider, RerankerProvider

logger = logging.getLogger(__name__)

_llm_provider: LLMProvider | None = None
_embed_provider: EmbeddingProvider | None = None
_rerank_provider: RerankerProvider | None = None

def get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        if settings.ai_llm_provider == 'groq':
            from app.ai.providers.groq_provider import GroqLLMProvider
            _llm_provider = GroqLLMProvider(api_key=settings.groq_api_key, model=settings.groq_llm_model)
        elif settings.ai_llm_provider == 'openai':
            from app.ai.providers.openai_provider import OpenAILLMProvider
            _llm_provider = OpenAILLMProvider(api_key=settings.openai_api_key, model=settings.openai_llm_model)
        elif settings.ai_llm_provider == 'anthropic':
            from app.ai.providers.anthropic_provider import AnthropicLLMProvider
            _llm_provider = AnthropicLLMProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_llm_model)
        else:
            raise ValueError(f'Unknown LLM provider: {settings.ai_llm_provider}')
    return _llm_provider

class FallbackEmbeddingWrapper(EmbeddingProvider):
    def __init__(self, primary: EmbeddingProvider):
        self.primary = primary
        self._dimensions = primary.dimensions
        from app.ai.providers.cohere_embed_provider import CohereEmbeddingProvider
        self.fallback = CohereEmbeddingProvider(
            api_key=settings.cohere_api_key,
            target_dimensions=self._dimensions
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return await self.primary.embed(texts)
        except Exception as e:
            logger.warning(f"Primary embedding provider failed ({e}). Falling back to Cohere embedding provider.")
            return await self.fallback.embed(texts)

    @property
    def dimensions(self) -> int:
        return self._dimensions

def get_embed_provider() -> EmbeddingProvider:
    global _embed_provider
    if _embed_provider is None:
        if settings.ai_embed_provider == 'bgem3':
            from app.ai.providers.bgem3_provider import BGEM3EmbeddingProvider
            primary = BGEM3EmbeddingProvider()
        elif settings.ai_embed_provider == 'gemini':
            from app.ai.providers.gemini_embed_provider import GeminiEmbeddingProvider
            primary = GeminiEmbeddingProvider(api_key=settings.google_api_key, model=settings.gemini_embed_model)
        elif settings.ai_embed_provider == 'openai':
            from app.ai.providers.openai_provider import OpenAIEmbeddingProvider
            primary = OpenAIEmbeddingProvider(
                api_key=settings.openai_api_key, 
                model=settings.openai_embed_model, 
                dimensions=settings.openai_embed_dimensions
            )
        else:
            raise ValueError(f'Unknown Embedding provider: {settings.ai_embed_provider}')
        
        if settings.ai_embed_fallback_provider == 'cohere':
            _embed_provider = FallbackEmbeddingWrapper(primary)
        else:
            _embed_provider = primary

    return _embed_provider

def get_rerank_provider() -> RerankerProvider:
    global _rerank_provider
    if _rerank_provider is None:
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
