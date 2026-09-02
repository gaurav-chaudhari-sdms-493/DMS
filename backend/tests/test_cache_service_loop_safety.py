"""Regression test for the Redis pool / event-loop bug found 2026-09-02
while checking OCR pipeline logs: cache_service.py's module-level
_redis_pool is reused across Celery tasks, each of which runs its own
fresh asyncio.run() loop that closes when the task ends. The old guard in
get_redis() tried to detect a stale pool by introspecting
_redis_pool.connection_pool._loop / _redis_pool._loop, but redis.asyncio
doesn't reliably expose the pool's bound loop under either name -- so a
pool created in a since-closed loop slipped through and raised "Event
loop is closed" on first real use (observed live: worker.log,
"Tenant cache invalidation notice ... Event loop is closed").

The fix tracks the loop get_redis() itself observed at pool-creation time
(_redis_pool_loop) instead of introspecting library internals. These
tests prove the new guard actually rebuilds instead of reusing a
loop-mismatched pool -- one test drives it through two genuinely
separate event loops (via asyncio.run(), same as a Celery task
boundary); the others set _redis_pool_loop directly to a sentinel that
can never equal the running loop, the simplest reliable way to assert
the mismatch branch fires without risking a second real event loop
deadlocking against pytest-asyncio's own running loop.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import cache_service


def _fake_redis_client(scan_result=(0, [])):
    client = MagicMock()
    client.aclose = AsyncMock()
    client.scan = AsyncMock(return_value=scan_result)
    client.delete = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def _reset_pool_state():
    cache_service._redis_pool = None
    cache_service._redis_pool_loop = None
    yield
    cache_service._redis_pool = None
    cache_service._redis_pool_loop = None


def test_get_redis_rebuilds_pool_across_separate_event_loops():
    """A pool created in one asyncio.run() loop must never be reused in a
    later, separate asyncio.run() loop -- the exact shape of a Celery
    worker handling two tasks back to back."""
    import asyncio

    seen_pools = []

    with patch.object(cache_service.aioredis, "from_url", side_effect=lambda *a, **k: _fake_redis_client()):
        async def acquire_once():
            async with cache_service.get_redis() as r:
                seen_pools.append(r)

        asyncio.run(acquire_once())  # loop A
        pool_after_loop_a = cache_service._redis_pool

        asyncio.run(acquire_once())  # loop B -- a fresh, separate loop
        pool_after_loop_b = cache_service._redis_pool

    assert seen_pools[0] is pool_after_loop_a
    assert seen_pools[1] is pool_after_loop_b
    assert pool_after_loop_a is not pool_after_loop_b, (
        "get_redis() reused a pool created in a different (closed) event "
        "loop instead of rebuilding -- this is the exact bug that produced "
        "'Event loop is closed' in production"
    )


@pytest.mark.asyncio
async def test_get_redis_reuses_pool_within_the_same_loop():
    with patch.object(cache_service.aioredis, "from_url", side_effect=lambda *a, **k: _fake_redis_client()):
        async with cache_service.get_redis() as r1:
            pass
        async with cache_service.get_redis() as r2:
            pass

    assert r1 is r2, "a pool created and used in the same live event loop should never be rebuilt"


@pytest.mark.asyncio
async def test_invalidate_tenant_cache_succeeds_after_loop_migration():
    """End-to-end shape of the real bug: invalidate_tenant_cache must not
    silently warn-and-no-op just because a stale pool from a different
    (e.g. a prior, now-closed Celery task's) loop is sitting in the
    module global -- it should rebuild and actually delete the matching
    keys instead of raising/being swallowed as a warning."""
    stale_pool = _fake_redis_client()
    cache_service._redis_pool = stale_pool
    cache_service._redis_pool_loop = object()  # a loop reference that is never the running loop

    with patch.object(
        cache_service.aioredis, "from_url",
        side_effect=lambda *a, **k: _fake_redis_client(scan_result=(0, ["search:tenant-x:abc"])),
    ):
        await cache_service.invalidate_tenant_cache("tenant-x")

    fresh_pool = cache_service._redis_pool
    assert fresh_pool is not stale_pool
    stale_pool.scan.assert_not_awaited()
    fresh_pool.delete.assert_awaited_once_with("search:tenant-x:abc")
