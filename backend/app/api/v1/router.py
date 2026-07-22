from fastapi import APIRouter
from . import auth, documents, search, folders

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth.router, prefix='/auth', tags=['auth'])
api_router.include_router(documents.router, prefix='/documents', tags=['documents'])
api_router.include_router(folders.router)
api_router.include_router(search.router, prefix='/search', tags=['search'])