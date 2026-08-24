import time
from typing import Any, Dict, Optional

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.sys_config import SysConfig

_CACHE_TTL_SECONDS = 60

_cache: Dict[str, Any] = {}
_cache_loaded_at: float = 0.0


async def _ensure_cache_fresh() -> None:
    global _cache_loaded_at
    now = time.time()
    if _cache and (now - _cache_loaded_at) < _CACHE_TTL_SECONDS:
        return

    async with AsyncSessionLocal() as db:
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
