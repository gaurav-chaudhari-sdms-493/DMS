import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.sys_config import SysConfig
from app.services.audit_service import log_action

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


async def get_str(key: str, default: str) -> str:
    return str(await get_config(key, default))


# T03 — the admin settings screen. Reads/writes through the caller's own
# request-scoped `db` (get_tenant_db), not this module's own NullPool
# _ConfigSession -- that one exists solely for the read-path's cross-loop
# safety (see the comment above), and an admin edit is a single request on
# the normal request-response path with no such loop-lifetime concern.
async def list_all_config(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(select(SysConfig).order_by(SysConfig.key))
    rows = result.scalars().all()
    return [
        {
            "key": row.key,
            "value": row.value.get("v") if isinstance(row.value, dict) else row.value,
            "description": row.description,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


async def set_config(db: AsyncSession, key: str, value: float, actor_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
    """Edits an EXISTING threshold only -- deliberately refuses to create a
    new key. A key nothing in the pipeline reads via get_int/get_float
    would just sit there doing nothing, silently misleading whoever typed
    it into thinking they'd changed real behavior. A genuinely new
    threshold still needs a migration (same seeding pattern as 0009,
    0028, 0030, 0040, 0041), because it needs a *default* for the
    environments that haven't set it yet -- this endpoint has no way to
    supply one."""
    row = await db.get(SysConfig, key)
    if not row:
        raise HTTPException(status_code=404, detail=f"No config key '{key}' exists — see set_config()'s own docstring for why this doesn't create one")

    old_value = row.value.get("v") if isinstance(row.value, dict) else row.value
    row.value = {"v": value}
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "config.update",
        resource_type="sys_config", resource_id=None,
        details={"key": key, "old_value": old_value, "new_value": value},
    )
    await db.commit()

    # Invalidate the read cache immediately rather than waiting up to
    # _CACHE_TTL_SECONDS -- an admin who just changed a threshold and
    # watches the next document process through the old value would
    # reasonably read that as the edit not having worked.
    global _cache_loaded_at
    _cache_loaded_at = 0.0

    return {"key": key, "value": value, "description": row.description, "updated_at": row.updated_at}
