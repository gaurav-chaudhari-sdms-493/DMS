from fastapi import APIRouter
from app.api.v1 import auth, documents, search

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth.router, prefix='/auth', tags=['auth'])
api_router.include_router(documents.router, prefix='/documents', tags=['documents'])
api_router.include_router(search.router, prefix='/search', tags=['search'])
