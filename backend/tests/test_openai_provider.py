import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.providers.openai_provider import OpenAIEmbeddingProvider


@pytest.mark.asyncio
async def test_openai_embedding_provider_empty_input():
    provider = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-small", dimensions=1536)
    res = await provider.embed([])
    assert res == []


@pytest.mark.asyncio
async def test_openai_embedding_provider_batches_using_configured_size():
    """T03 — request batch size is sourced from sys_dg_config
    (embed_api_batch_size), not hardcoded to 100."""
    provider = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-small", dimensions=4)

    def _fake_response(**kwargs):
        batch = kwargs["input"]
        resp = MagicMock()
        resp.data = [MagicMock(embedding=[0.0, 0.0, 0.0, 0.0]) for _ in batch]
        return resp

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(side_effect=_fake_response)

    texts = [f"text {i}" for i in range(5)]
    with patch("app.ai.providers.openai_provider.AsyncOpenAI", return_value=mock_client):
        with patch("app.ai.providers.openai_provider.get_int", new=AsyncMock(return_value=2)) as mock_get_int:
            embeddings = await provider.embed(texts)

    mock_get_int.assert_called_once_with("embed_api_batch_size", 100)
    assert len(embeddings) == 5
    # batch_size=2 over 5 texts -> 3 calls (2, 2, 1)
    assert mock_client.embeddings.create.await_count == 3
