import logging
from fastapi import APIRouter
from sqlalchemy import text
import redis.asyncio as aioredis
from app.config import settings
from app.ai.factory import get_embed_provider
from app.database import AsyncSessionLocal, AppSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/health')
async def health_check():
    checks = {}

    # 1. Embedding Provider check
    try:
        provider = get_embed_provider()
        vec = await provider.embed(["health check"])
        checks["embeddings"] = {
            "status": "ok",
            "provider": type(provider).__name__,
            "dimensions": len(vec[0]) if vec and len(vec) > 0 else 0,
        }
    except Exception as e:
        checks["embeddings"] = {"status": "error", "detail": str(e)}

    # 2. Database check
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # 3. Redis check
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    # 4. RLS check — real gap found live 2026-09-09: this endpoint's README
    # implies it verifies RLS, but it never checked anything RLS-related at
    # all. Proving true cross-tenant isolation needs a second real tenant's
    # data to attempt reading (out of scope for a health check), but the
    # structural precondition D-2 actually depends on IS cheaply verifiable
    # here: every real request goes through AppSessionLocal's `dms_app` role
    # (see database.py's D-2 comment), and RLS provides no protection at all
    # if that role can bypass it — a superuser or BYPASSRLS role ignores
    # every policy unconditionally, regardless of how the policies
    # themselves are written. So this checks the role FastAPI requests
    # actually run as, not the policies (which migration 0046 already owns).
    try:
        async with AppSessionLocal() as session:
            row = (await session.execute(text(
                "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            ))).one()
        if row.rolsuper or row.rolbypassrls:
            checks["rls"] = {
                "status": "error",
                "detail": "app DB role can bypass Row-Level Security (rolsuper or rolbypassrls) — policies provide no real protection",
            }
        else:
            checks["rls"] = {"status": "ok", "detail": "app DB role cannot bypass Row-Level Security"}
    except Exception as e:
        checks["rls"] = {"status": "error", "detail": str(e)}

    overall = "ok" if all(c.get("status") == "ok" for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
