from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.router import api_router
from app.services.cache_service import init_redis

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
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
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    @app.get("/")
    async def root():
        return {
            "title": settings.app_env,
            "status": "online",
            "docs": "/api/docs",
            "version": "1.0.0"
        }

    app.include_router(api_router)
    
    return app

app = create_app()

