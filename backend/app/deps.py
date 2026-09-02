from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from .database import AsyncSessionLocal, get_db  # noqa: F401 — re-exported; 13 API route files import get_db from here, not from .database directly
from .services.auth_service import verify_token
from .schemas.auth import TokenPayload

bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> TokenPayload:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(credentials.credentials)
    if payload.type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload

async def require_tenant_access(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if not current_user or not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context")
    return current_user


def require_role(*allowed_roles: str):
    """T50 — reusable role-gate dependency, e.g. Depends(require_role('it_admin', 'auditor')).
    Replaces the old pattern of a plain function called manually inside a
    handler body (admin.py's require_admin), which doesn't compose across
    many endpoints for six personas.
    """
    async def _check(current_user: TokenPayload = Depends(require_tenant_access)) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of: {', '.join(allowed_roles)}",
            )
        return current_user
    return _check

async def get_tenant_db(
    current_user: TokenPayload = Depends(require_tenant_access),
):
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :t, false)"),
                {"t": str(current_user.tenant_id)}
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "127.0.0.1"