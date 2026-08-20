import pytest
from app.config import settings
from app.ai.factory import get_rerank_provider
from app.ai.providers.cohere_provider import CohereRerankerProvider

def test_cohere_reranker_default_configuration():
    assert settings.ai_rerank_provider == "cohere"
    reranker = get_rerank_provider()
    assert isinstance(reranker, CohereRerankerProvider)
    assert reranker.model == settings.cohere_rerank_model

@pytest.mark.asyncio
async def test_cohere_reranker_execution():
    reranker = get_rerank_provider("cohere")
    docs = ["This is document 1", "This is document 2"]
    results = await reranker.rerank("document", docs, top_n=2)
    assert len(results) <= 2
    for r in results:
        assert 0 <= r.index < len(docs)
        assert isinstance(r.score, float)
