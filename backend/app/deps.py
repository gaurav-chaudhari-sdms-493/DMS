from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, set_tenant_context
from app.services.auth_service import verify_token
from app.schemas.auth import TokenPayload
import uuid

bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> TokenPayload:
    return verify_token(credentials.credentials)

async def require_tenant_access(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context")
    return current_user

async def get_db_with_tenant(
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_tenant_access),
) -> AsyncSession:
    """Dependency providing a DB session with transaction-scoped tenant RLS context."""
    await set_tenant_context(db, current_user.tenant_id)
    return db

async def get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "127.0.0.1"

