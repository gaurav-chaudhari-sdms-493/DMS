from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from .config import settings
from .api.v1.router import api_router
from .services.cache_service import init_redis
from .tasks.worker import celery_app

from .services.storage_service import ensure_bucket_exists, ensure_archive_bucket_exists
from .services.connector_base import get_enabled_connectors
from .api_logging_middleware import ApiLoggingMiddleware

from .limiter import limiter
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await ensure_bucket_exists()
    try:
        # T64/T93 — previously a manual runbook step ("Known gap to check
        # manually"); the archive bucket must exist WITH Object Lock before
        # any WORM archival call, and Object Lock can only be set at bucket
        # creation, so this has to run before anything else touches it.
        # Best-effort: WORM archival is an auxiliary evidence feature, not
        # core to the app serving traffic — a hiccup here must never block
        # startup the way a missing operational-documents bucket would.
        await ensure_archive_bucket_exists()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"T64 WORM archive bucket setup failed at startup: {e}")
    # T40 — connectors are a typed contract (services/connector_base.py);
    # a new connector is added to get_enabled_connectors(), never here.
    connector_tasks = [asyncio.create_task(c.run_loop()) for c in get_enabled_connectors()]
    yield
    for task in connector_tasks:
        task.cancel()

def create_app() -> FastAPI:
    app = FastAPI(
        title='Document Search Engine',
        description='Multi-tenant AI document search and retrieval platform',
        version='1.0.0',
        lifespan=lifespan,
        docs_url='/api/docs',
        redoc_url='/api/redoc',
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API call logging middleware (runs after CORS)
    app.add_middleware(ApiLoggingMiddleware)
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    app.include_router(api_router)
    
    # Attach Celery app to the FastAPI app instance
    app.celery_app = celery_app
    
    return app

app = create_app()