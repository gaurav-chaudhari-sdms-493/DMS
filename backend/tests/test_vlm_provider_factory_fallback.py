"""Confirms get_vlm_provider() actually wires FallbackVLMProvider when
OpenRouter is primary and a GOOGLE_API_KEY is also configured -- the
factory-level half of the fallback feature (backend/tests/
test_fallback_vlm_provider.py covers the wrapper's own behavior)."""
import pytest

from app.ai import factory
from app.ai.providers.fallback_vlm_provider import FallbackVLMProvider
from app.ai.providers.gemini_provider import GeminiVLMProvider
from app.ai.providers.openrouter_provider import OpenRouterVLMProvider


@pytest.fixture(autouse=True)
def _reset_vlm_provider_cache():
    factory._vlm_provider = False
    yield
    factory._vlm_provider = False


def test_openrouter_primary_with_google_key_wraps_in_fallback(monkeypatch):
    monkeypatch.setattr(factory.settings, "ai_vlm_provider", "openrouter")
    monkeypatch.setattr(factory.settings, "openrouter_api_key", "or-test-key")
    monkeypatch.setattr(factory.settings, "google_api_key", "google-test-key")
    monkeypatch.setattr(factory.settings, "air_gapped", False)

    provider = factory.get_vlm_provider()

    assert isinstance(provider, FallbackVLMProvider)
    assert isinstance(provider.primary, OpenRouterVLMProvider)
    assert isinstance(provider.fallback, GeminiVLMProvider)


def test_openrouter_primary_without_google_key_stays_unwrapped(monkeypatch):
    monkeypatch.setattr(factory.settings, "ai_vlm_provider", "openrouter")
    monkeypatch.setattr(factory.settings, "openrouter_api_key", "or-test-key")
    monkeypatch.setattr(factory.settings, "google_api_key", "")
    monkeypatch.setattr(factory.settings, "air_gapped", False)

    provider = factory.get_vlm_provider()

    assert isinstance(provider, OpenRouterVLMProvider)
    assert not isinstance(provider, FallbackVLMProvider)


def test_gemini_primary_is_never_wrapped_in_itself(monkeypatch):
    monkeypatch.setattr(factory.settings, "ai_vlm_provider", "gemini")
    monkeypatch.setattr(factory.settings, "google_api_key", "google-test-key")
    monkeypatch.setattr(factory.settings, "air_gapped", False)

    provider = factory.get_vlm_provider()

    assert isinstance(provider, GeminiVLMProvider)
    assert not isinstance(provider, FallbackVLMProvider)
