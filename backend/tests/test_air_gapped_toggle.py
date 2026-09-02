import pytest
from app.config import settings
import app.ai.factory as factory
import app.ocr.factory as ocr_factory
from app.ai.airgapped import AirGappedViolation


def _reset_factory_caches():
    factory._llm_provider = None
    factory._embed_provider = None
    factory._rerank_providers_by_name = {}
    factory._vlm_provider = False
    ocr_factory._ocr_provider = None


@pytest.fixture(autouse=True)
def _isolate_air_gapped_state():
    snapshot = {
        "air_gapped": settings.air_gapped,
        "ai_embed_provider": settings.ai_embed_provider,
        "ai_embed_fallback_provider": settings.ai_embed_fallback_provider,
        "ai_rerank_provider": settings.ai_rerank_provider,
        "ai_ocr_provider": settings.ai_ocr_provider,
        "ai_vlm_provider": settings.ai_vlm_provider,
        "google_api_key": settings.google_api_key,
        "cohere_api_key": settings.cohere_api_key,
    }
    _reset_factory_caches()
    yield
    for key, value in snapshot.items():
        setattr(settings, key, value)
    _reset_factory_caches()


def test_air_gapped_blocks_llm_provider():
    """T91 (partial) — no local LLM provider exists yet (T90), so every
    ai_llm_provider choice is external and must be refused under AIR_GAPPED."""
    settings.air_gapped = True
    with pytest.raises(AirGappedViolation):
        factory.get_llm_provider()


def test_air_gapped_blocks_vlm_gemini():
    settings.air_gapped = True
    settings.ai_vlm_provider = "gemini"
    settings.google_api_key = "fake-key-for-test"
    with pytest.raises(AirGappedViolation):
        factory.get_vlm_provider()


def test_air_gapped_allows_local_embed_and_ocr():
    """bgem3 (embeddings) and pdfplumber (OCR) are genuinely local today —
    air-gapped mode must not block them."""
    settings.air_gapped = True
    settings.ai_embed_provider = "bgem3"
    settings.ai_embed_fallback_provider = "none"
    provider = factory.get_embed_provider()
    assert provider is not None

    settings.ai_ocr_provider = "pdfplumber"
    ocr = ocr_factory.get_ocr_provider()
    assert ocr is not None


def test_air_gapped_blocks_external_embed_provider():
    settings.air_gapped = True
    settings.ai_embed_provider = "openai"
    with pytest.raises(AirGappedViolation):
        factory.get_embed_provider()


def test_air_gapped_blocks_llamaparse_ocr():
    settings.air_gapped = True
    settings.ai_ocr_provider = "llamaparse"
    with pytest.raises(AirGappedViolation):
        ocr_factory.get_ocr_provider()


def test_air_gapped_suppresses_cohere_rerank_auto_upgrade():
    """Outside air-gapped mode, a configured Cohere key silently upgrades a
    'bgem3' rerank choice to Cohere (see factory.py). Under AIR_GAPPED that
    silent external upgrade must not happen — it stays on the local model."""
    settings.air_gapped = True
    settings.ai_rerank_provider = "bgem3"
    settings.cohere_api_key = "fake-key"
    provider = factory.get_rerank_provider()
    assert provider.__class__.__name__ == "BGEM3RerankerProvider"


def test_air_gapped_blocks_explicit_cohere_rerank():
    settings.air_gapped = True
    settings.ai_rerank_provider = "cohere"
    with pytest.raises(AirGappedViolation):
        factory.get_rerank_provider()


def test_not_air_gapped_allows_external_providers():
    """Sanity check: with the toggle off, external providers still resolve
    normally (construction only — no real network call made in this test)."""
    settings.air_gapped = False
    provider = factory.get_llm_provider()
    assert provider is not None


def test_explicit_bgem3_override_is_respected_even_with_cohere_key():
    """Regression — found live during the T92 E2E pass: a user explicitly
    picking 'Local (BGE)' in Search Settings (override='bgem3') got Cohere
    anyway whenever a Cohere key was configured, because the
    auto-upgrade-to-cohere heuristic didn't distinguish an explicit
    per-request choice from the tenant-wide default. It must only apply
    when there's no explicit override."""
    settings.air_gapped = False
    settings.cohere_api_key = "fake-key"
    provider = factory.get_rerank_provider(override="bgem3")
    assert provider.__class__.__name__ == "BGEM3RerankerProvider"
