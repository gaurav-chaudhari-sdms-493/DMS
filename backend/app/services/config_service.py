import time
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.sys_config import SysConfig

_CACHE_TTL_SECONDS = 60

_cache: Dict[str, Any] = {}
_cache_loaded_at: float = 0.0

# This module is called from both the long-lived backend API process (one
# event loop for the process lifetime — app.database's pooled AsyncSessionLocal
# is fine there) and Celery tasks (a fresh event loop per asyncio.run() call —
# a pooled connection checked out during one task can be handed to a LATER
# task's different, by-then-closed loop, raising "RuntimeError: Event loop is
# closed" / "Future attached to a different loop"). Real bug: found live
# during OCR pipeline verification 2026-09-01 — get_int()/get_float() are
# called on every ingestion task (chunk_size_tokens, embed_local_batch_size,
# etc.), each one hitting this shared-engine refresh whenever the 60s cache
# goes stale, intermittently poisoning the pool for whichever task's loop
# happens to be active at that moment. NullPool means every checkout is a
# genuinely fresh connection with nothing pooled to go stale — safe from
# either calling context, and the overhead is negligible since this runs at
# most once per 60 seconds.
_config_engine = create_async_engine(settings.postgres_url, poolclass=NullPool)
_ConfigSession = async_sessionmaker(_config_engine, class_=AsyncSession, expire_on_commit=False)


async def _ensure_cache_fresh() -> None:
    global _cache_loaded_at
    now = time.time()
    if _cache and (now - _cache_loaded_at) < _CACHE_TTL_SECONDS:
        return

    async with _ConfigSession() as db:
        result = await db.execute(select(SysConfig))
        rows = result.scalars().all()

    _cache.clear()
    for row in rows:
        _cache[row.key] = row.value.get("v") if isinstance(row.value, dict) else row.value
    _cache_loaded_at = now


async def get_config(key: str, default: Optional[Any] = None) -> Any:
    """Read a config value by key, falling back to `default` if the row is missing."""
    await _ensure_cache_fresh()
    return _cache.get(key, default)


async def get_int(key: str, default: int) -> int:
    return int(await get_config(key, default))


async def get_float(key: str, default: float) -> float:
    return float(await get_config(key, default))
