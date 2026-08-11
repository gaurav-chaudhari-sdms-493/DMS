import logging
from fastapi import APIRouter
from sqlalchemy import text
import redis.asyncio as aioredis
from app.config import settings
from app.ai.factory import get_embed_provider
from app.database import AsyncSessionLocal

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

    overall = "ok" if all(c.get("status") == "ok" for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
