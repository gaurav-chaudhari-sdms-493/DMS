import pytest_asyncio
from app.database import engine
from app.services.cache_service import close_redis

@pytest_asyncio.fixture(autouse=True)
async def cleanup_connections_after_test():
    yield
    await engine.dispose()
    await close_redis()
