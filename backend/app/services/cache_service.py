import hashlib
import json
import asyncio
import logging
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from typing import Optional
from app.config import settings
from app.schemas.search import SearchResponse

logger = logging.getLogger(__name__)

_redis_pool = None
# The loop get_redis() itself observed via asyncio.get_running_loop() at
# creation time -- NOT introspected from redis-py internals. The previous
# guard read _redis_pool.connection_pool._loop / _redis_pool._loop, but
# redis.asyncio doesn't reliably expose the pool's bound loop under either
# name across versions, so a stale pool from a closed loop (the backend's
# single long-lived loop is fine, but each Celery task runs its own fresh
# asyncio.run() loop that closes when the task ends, same anti-pattern as
# the DB engine bug fixed in worker.py/config_service.py) slipped past the
# check and raised "Event loop is closed" on first real use -- caught and
# logged as a warning by every caller below, so ingestion never failed, but
# tenant cache invalidation silently no-op'd. Tracking our own loop
# reference removes the dependency on those internals entirely.
_redis_pool_loop = None

async def init_redis():
    global _redis_pool, _redis_pool_loop
    _redis_pool = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    _redis_pool_loop = asyncio.get_running_loop()

async def close_redis():
    global _redis_pool, _redis_pool_loop
    if _redis_pool:
        try:
            await _redis_pool.aclose()
        except Exception:
            pass
        _redis_pool = None
        _redis_pool_loop = None

@asynccontextmanager
async def get_redis():
    global _redis_pool, _redis_pool_loop
    if _redis_pool is not None and _redis_pool_loop is not asyncio.get_running_loop():
        _redis_pool = None
        _redis_pool_loop = None

    if not _redis_pool:
        await init_redis()
    yield _redis_pool

def generate_cache_key(tenant_id: str, query: str, filters: Optional[dict] = None) -> str:
    raw = f"{tenant_id}:{query}:{json.dumps(filters, sort_keys=True)}"
    return f"search:{tenant_id}:{hashlib.sha256(raw.encode()).hexdigest()}"

async def get_cached_search(cache_key: str) -> Optional[SearchResponse]:
    try:
        async with get_redis() as r:
            data = await r.get(cache_key)
            if data:
                try:
                    resp = SearchResponse.model_validate_json(data)
                    resp.cached = True
                    return resp
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Failed to fetch cached search: {e}")
    return None

async def cache_search_result(cache_key: str, result: SearchResponse, ttl: int = 300) -> None:
    try:
        async with get_redis() as r:
            await r.set(cache_key, result.model_dump_json(), ex=ttl)
    except Exception as e:
        logger.warning(f"Failed to set cached search result: {e}")

async def invalidate_tenant_cache(tenant_id: str) -> None:
    try:
        async with get_redis() as r:
            cursor = "0"
            while cursor != 0:
                cursor, keys = await r.scan(cursor=cursor, match=f"search:{tenant_id}:*")
                if keys:
                    await r.delete(*keys)
    except Exception as e:
        logger.warning(f"Tenant cache invalidation notice for {tenant_id}: {e}")
