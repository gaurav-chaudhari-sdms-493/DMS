import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from app.ai.providers.bgem3_provider import BGEM3EmbeddingProvider
from app.ai.factory import get_embed_provider
from app.config import settings

@pytest.mark.asyncio
async def test_bgem3_provider_dimensions():
    provider = BGEM3EmbeddingProvider()
    assert provider.dimensions == 1024

@pytest.mark.asyncio
async def test_bgem3_provider_empty_input():
    provider = BGEM3EmbeddingProvider()
    res = await provider.embed([])
    assert res == []

@pytest.mark.asyncio
async def test_bgem3_provider_embed_mocked():
    provider = BGEM3EmbeddingProvider()
    
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((2, 1024), dtype=np.float32)
    provider._model = mock_model

    texts = ["hello world", "test embedding document"]
    embeddings = await provider.embed(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1024
    assert len(embeddings[1]) == 1024

@pytest.mark.asyncio
async def test_bgem3_provider_embed_uses_configured_batch_size():
    """T03 — embed batch size is sourced from sys_dg_config
    (embed_local_batch_size), not hardcoded on the encode() call."""
    provider = BGEM3EmbeddingProvider()

    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((1, 1024), dtype=np.float32)
    provider._model = mock_model

    with patch('app.ai.providers.bgem3_provider.get_int', new=AsyncMock(return_value=8)) as mock_get_int:
        await provider.embed(["hello world"])

    mock_get_int.assert_called_once_with("embed_local_batch_size", 32)
    _, kwargs = mock_model.encode.call_args
    assert kwargs["batch_size"] == 8


def test_bgem3_factory_resolution():
    with patch.object(settings, 'ai_embed_provider', 'bgem3'):
        with patch.object(settings, 'ai_embed_fallback_provider', 'none'):
            with patch('app.ai.factory._embed_provider', None):
                provider = get_embed_provider()
                assert provider.__class__.__name__ == 'BGEM3EmbeddingProvider'
                assert provider.dimensions == 1024
