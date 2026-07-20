import hashlib
import json
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from typing import Optional
from app.config import settings
from app.schemas.search import SearchResponse

_redis_pool = None

async def init_redis():
    global _redis_pool
    _redis_pool = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

@asynccontextmanager
async def get_redis():
    if not _redis_pool:
        await init_redis()
    yield _redis_pool

def generate_cache_key(tenant_id: str, query: str, filters: Optional[dict] = None) -> str:
    raw = f"{tenant_id}:{query}:{json.dumps(filters, sort_keys=True)}"
    return f"search:{tenant_id}:{hashlib.sha256(raw.encode()).hexdigest()}"

async def get_cached_search(cache_key: str) -> Optional[SearchResponse]:
    async with get_redis() as r:
        data = await r.get(cache_key)
        if data:
            try:
                resp = SearchResponse.model_validate_json(data)
                resp.cached = True
                return resp
            except Exception:
                pass
    return None

async def cache_search_result(cache_key: str, result: SearchResponse, ttl: int = 300) -> None:
    async with get_redis() as r:
        await r.set(cache_key, result.model_dump_json(), ex=ttl)

async def invalidate_tenant_cache(tenant_id: str) -> None:
    async with get_redis() as r:
        cursor = "0"
        while cursor != 0:
            cursor, keys = await r.scan(cursor=cursor, match=f"search:{tenant_id}:*")
            if keys:
                await r.delete(*keys)
