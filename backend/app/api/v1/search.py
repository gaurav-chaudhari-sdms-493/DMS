from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from ...schemas.search import SearchRequest, SearchResponse
from ...schemas.auth import TokenPayload
from ...deps import get_db, require_tenant_access, get_request_ip
from ...services.search_service import search as do_search
import uuid

router = APIRouter()

@router.post('/', response_model=SearchResponse)
async def search(
    body: SearchRequest,
    request: Request,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    ip_addr = await get_request_ip(request)
    
    return await do_search(
        query=body.query,
        tenant_id=tenant_id,
        user_id=user_id,
        limit=body.limit,
        filters=body.filters,
        db=db,
        ip_address=ip_addr,
        rerank_provider=body.rerank_provider,
        generate_summary=body.generate_summary
    )