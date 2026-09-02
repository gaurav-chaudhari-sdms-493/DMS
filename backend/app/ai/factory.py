from app.config import settings
from app.ai.airgapped import enforce_local
from app.ai.base import LLMProvider, EmbeddingProvider, RerankerProvider, VLMProvider, Message
from typing import List

import logging

logger = logging.getLogger(__name__)

_llm_provider: LLMProvider | None = None
_embed_provider: EmbeddingProvider | None = None
_rerank_providers_by_name: dict[str, RerankerProvider] = {}
_vlm_provider: VLMProvider | None | bool = False  # False = not yet resolved

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

    # No local LLM provider exists yet (T90, not built) — groq/openai/anthropic
    # are all external APIs, so air-gapped mode has nothing valid to select.
    enforce_local('LLM', settings.ai_llm_provider)

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
        enforce_local('embeddings', 'openai')
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
        enforce_local('embeddings', 'gemini')
        from app.ai.providers.gemini_provider import GeminiEmbeddingProvider
        primary_provider = GeminiEmbeddingProvider(api_key=settings.google_api_key, model=settings.gemini_embed_model)
    elif settings.ai_embed_provider == 'cohere':
        enforce_local('embeddings', 'cohere')
        from app.ai.providers.cohere_provider import CohereEmbeddingProvider
        primary_provider = CohereEmbeddingProvider(api_key=settings.cohere_api_key, model="embed-english-v3.0")
    else:
        raise ValueError(f'Unknown Embedding provider: {settings.ai_embed_provider}')

    fallback_provider = None
    if settings.ai_embed_fallback_provider == 'cohere':
        enforce_local('embeddings fallback', 'cohere')
        from app.ai.providers.cohere_provider import CohereEmbeddingProvider
        fallback_provider = CohereEmbeddingProvider(api_key=settings.cohere_api_key, model="embed-english-v3.0")
    elif settings.ai_embed_fallback_provider == 'openai':
        enforce_local('embeddings fallback', 'openai')
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


def _build_rerank_provider(name: str) -> RerankerProvider:
    if name == 'cohere':
        enforce_local('reranker', 'cohere')
        from app.ai.providers.cohere_provider import CohereRerankerProvider
        return CohereRerankerProvider(api_key=settings.cohere_api_key, model=settings.cohere_rerank_model)
    elif name == 'bgem3':
        from app.ai.providers.bge_reranker_provider import BGEM3RerankerProvider
        return BGEM3RerankerProvider(model_name=settings.bgem3_rerank_model)
    else:
        class DummyReranker(RerankerProvider):
            async def rerank(self, query: str, documents: list[str], top_n: int = 5):
                from app.ai.base import RankedResult
                return [RankedResult(index=i, score=1.0, text=d) for i, d in enumerate(documents[:top_n])]
        return DummyReranker()


def get_rerank_provider(override: str | None = None) -> RerankerProvider:
    """Return the configured reranker, or a specific one via `override` (e.g. per-request choice).

    Providers are cached by name so switching between them per-request never re-triggers
    an expensive model reload (notably the local BGE cross-encoder).
    """
    name = override or settings.ai_rerank_provider
    # Ensure local BGE cross-encoder is never loaded BY DEFAULT when Cohere
    # API key is configured — but never override an explicit per-request
    # choice (override=...), and never in air-gapped mode, where
    # auto-upgrading to an external API is exactly the silent-fallback
    # behavior T91 exists to prevent. Without the `override is None` guard,
    # a user explicitly picking "Local (BGE)" in Search Settings silently
    # got Cohere anyway whenever a Cohere key was configured (the default) —
    # found live during the T92 E2E pass.
    if override is None and (name == 'bgem3' or not name) and settings.cohere_api_key and not settings.air_gapped:
        name = 'cohere'

    if name not in _rerank_providers_by_name:
        _rerank_providers_by_name[name] = _build_rerank_provider(name)
    return _rerank_providers_by_name[name]


def get_vlm_provider() -> VLMProvider | None:
    """T22 — returns None (not an error) when VLM extraction is disabled or
    unconfigured, since it's an optional enrichment step on top of chunk
    indexing, not something ingestion should ever fail over.

    T90 note: app/ai/providers/qwen_vlm_provider.py (QwenVLMProvider)
    exists as an UNTESTED/UNVERIFIED local-VLM scaffold — deliberately
    NOT wired in here as a selectable ai_vlm_provider value, since no GPU
    was available to actually validate it (see the class's own docstring
    for why). Wiring it in is real follow-up work, not a config flip,
    once someone with GPU hardware has run and verified it.

    Automatic fallback: if the primary provider isn't already gemini and
    a GOOGLE_API_KEY is configured, wraps it in FallbackVLMProvider so a
    primary-provider failure (e.g. OpenRouter running out of credits —
    a real live incident, 2026-09-02) retries against Gemini
    automatically instead of needing a manual AI_VLM_PROVIDER edit +
    restart. enforce_local() on the primary already refuses to start in
    air-gapped mode before this point, so no separate air-gapped check is
    needed for the fallback leg.
    """
    global _vlm_provider
    if _vlm_provider is not False:
        return _vlm_provider

    if settings.ai_vlm_provider == 'gemini' and settings.google_api_key:
        enforce_local('VLM', 'gemini')
        from app.ai.providers.gemini_provider import GeminiVLMProvider
        _vlm_provider = GeminiVLMProvider(api_key=settings.google_api_key, model=settings.gemini_vlm_model)
    elif settings.ai_vlm_provider == 'openrouter' and settings.openrouter_api_key:
        enforce_local('VLM', 'openrouter')
        from app.ai.providers.openrouter_provider import OpenRouterVLMProvider
        primary = OpenRouterVLMProvider(api_key=settings.openrouter_api_key, model=settings.openrouter_vlm_model)
        if settings.google_api_key:
            from app.ai.providers.gemini_provider import GeminiVLMProvider
            from app.ai.providers.fallback_vlm_provider import FallbackVLMProvider
            fallback = GeminiVLMProvider(api_key=settings.google_api_key, model=settings.gemini_vlm_model)
            _vlm_provider = FallbackVLMProvider(primary=primary, fallback=fallback, fallback_name="gemini")
        else:
            _vlm_provider = primary
    else:
        _vlm_provider = None

    return _vlm_provider
