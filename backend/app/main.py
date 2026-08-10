from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from .config import settings
from .api.v1.router import api_router
from .services.cache_service import init_redis
from .tasks.worker import celery_app

from .services.storage_service import ensure_bucket_exists
from .api_logging_middleware import ApiLoggingMiddleware

from .limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await ensure_bucket_exists()
    yield

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