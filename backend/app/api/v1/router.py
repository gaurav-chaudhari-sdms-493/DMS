from fastapi import APIRouter
from . import auth, documents, search, folders, chat, admin, health, connectors, facts, entities, records, governance, departments, export

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(health.router, tags=['health'])
api_router.include_router(auth.router, prefix='/auth', tags=['auth'])
api_router.include_router(documents.router, prefix='/documents', tags=['documents'])
api_router.include_router(folders.router)
api_router.include_router(search.router, prefix='/search', tags=['search'])
api_router.include_router(chat.router, prefix='/chat', tags=['chat'])
api_router.include_router(admin.router, prefix='/admin', tags=['admin'])
api_router.include_router(connectors.router)
api_router.include_router(facts.router)
api_router.include_router(entities.router)
api_router.include_router(records.router)
api_router.include_router(governance.router)
api_router.include_router(departments.router)
api_router.include_router(export.router)