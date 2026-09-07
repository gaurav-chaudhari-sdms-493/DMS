import pytest_asyncio
from app.database import engine, app_engine
from app.services.cache_service import close_redis

@pytest_asyncio.fixture(autouse=True)
async def cleanup_connections_after_test():
    yield
    await engine.dispose()
    # D-2 fix, 2026-09-07 — app_engine (the restricted-role connection
    # get_db/get_tenant_db actually use) is a second engine alongside the
    # one above; without disposing it too, a test that drives a real ASGI
    # request (test_email_webhook.py's is the only one) can leave a pooled
    # connection bound to that test's event loop, which the next test's
    # own loop then can't reuse ("attached to a different loop").
    await app_engine.dispose()
    await close_redis()
