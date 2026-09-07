"""Regression tests for FallbackVLMProvider, built 2026-09-02 after a real
live incident: the OpenRouter account ran out of credits mid-extraction
(402), and recovery required a manual AI_VLM_PROVIDER edit + container
restart even though a working GOOGLE_API_KEY was already configured.
These tests prove the wrapper actually falls back instead of just
looking like it should."""
from unittest.mock import AsyncMock

import pytest

from app.ai.providers.fallback_vlm_provider import FallbackVLMProvider


def _provider(return_value=None, side_effect=None):
    p = AsyncMock()
    if side_effect is not None:
        p.extract_structured = AsyncMock(side_effect=side_effect)
    else:
        p.extract_structured = AsyncMock(return_value=return_value)
    return p


@pytest.mark.asyncio
async def test_primary_success_never_touches_fallback():
    primary = _provider(return_value='{"rows": []}')
    fallback = _provider(return_value='{"rows": ["should never see this"]}')
    provider = FallbackVLMProvider(primary=primary, fallback=fallback, fallback_name="gemini")

    result = await provider.extract_structured(b"png", "prompt")

    assert result == '{"rows": []}'
    fallback.extract_structured.assert_not_awaited()


@pytest.mark.asyncio
async def test_primary_failure_retries_with_fallback():
    primary = _provider(side_effect=Exception("OpenRouter VLM request failed with status 402: out of credits"))
    fallback = _provider(return_value='{"rows": ["from gemini"]}')
    provider = FallbackVLMProvider(primary=primary, fallback=fallback, fallback_name="gemini")

    result = await provider.extract_structured(b"png", "prompt")

    assert result == '{"rows": ["from gemini"]}'
    primary.extract_structured.assert_awaited_once()
    fallback.extract_structured.assert_awaited_once()


@pytest.mark.asyncio
async def test_both_providers_failing_raises_the_primarys_error():
    primary_error = Exception("OpenRouter VLM request failed with status 402: out of credits")
    fallback_error = Exception("Gemini VLM request failed with status 429: rate limited")
    primary = _provider(side_effect=primary_error)
    fallback = _provider(side_effect=fallback_error)
    provider = FallbackVLMProvider(primary=primary, fallback=fallback, fallback_name="gemini")

    with pytest.raises(Exception) as exc_info:
        await provider.extract_structured(b"png", "prompt")

    assert exc_info.value is primary_error
