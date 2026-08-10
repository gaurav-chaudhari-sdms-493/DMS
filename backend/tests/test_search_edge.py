import pytest
import uuid
from app.services.guardrail_service import validate_output_summary
from app.services.search_service import search
from app.services.chat_service import _extract_score_threshold, _is_explicit_search_intent
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User


def test_validate_output_summary_edge_cases():
    """Verify validate_output_summary scrubs PII from summaries."""
    assert validate_output_summary(None) is None
    assert validate_output_summary("") == ""
    assert validate_output_summary("Contact admin@company.com") == "Contact [REDACTED_EMAIL]"


def test_extract_score_threshold_edge_cases():
    """Verify extracting score thresholds from dynamic chat queries."""
    assert _extract_score_threshold("filter score >= 95%") == 0.95
    assert _extract_score_threshold("score >= 100%") == 1.0
    assert _extract_score_threshold("score >= 0%") == 0.0
    assert _extract_score_threshold("score > 50") == 0.50
    assert _extract_score_threshold("give me top 5 documents") is None
    assert _extract_score_threshold("random query without score") is None


def test_explicit_search_intent_detection():
    """Verify detecting user query explicit search intent triggers."""
    assert _is_explicit_search_intent("search for Q3 financial reports") is True
    assert _is_explicit_search_intent("find invoice 104") is True
    assert _is_explicit_search_intent("look for contract details") is True
    assert _is_explicit_search_intent("what is the total revenue listed on page 3?") is False


@pytest.mark.asyncio
async def test_search_isolated_tenant_empty_results():
    """Verify searching in a newly created empty tenant returns 0 results cleanly without errors."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Empty Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"empty_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            res = await search(
                query="test query for empty tenant",
                tenant_id=tenant_id,
                user_id=user_id,
                limit=10,
                filters=None,
                db=db,
                ip_address="127.0.0.1"
            )
            assert res is not None
            assert len(res.results) == 0
        finally:
            await db.close()
