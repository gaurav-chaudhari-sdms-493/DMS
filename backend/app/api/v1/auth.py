from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...schemas.auth import LoginRequest, TokenResponse, TokenPayload, SignUpRequest, SignUpResponse
from ...models.user import User
from ...deps import get_db, get_current_user, get_request_ip
from ...services.auth_service import verify_password, create_access_token, create_refresh_token, sign_up
from ...services.audit_service import log_action

router = APIRouter()

@router.post('/sign-up', response_model=SignUpResponse, status_code=201)
async def sign_up_user(
    body: SignUpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant and an admin user."""
    new_user = await sign_up(body, db)
    ip_addr = await get_request_ip(request)
    
    await log_action(
        db=db,
        actor_id=new_user.user_id,
        tenant_id=new_user.tenant_id,
        action="auth.sign_up",
        resource_type="user",
        resource_id=new_user.user_id,
        ip_address=ip_addr,
        details={"email": new_user.email}
    )
    
    await db.commit()
    return new_user

@router.post('/login', response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == body.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    acc = create_access_token(user.id, user.tenant_id, user.role.value)
    ref = create_refresh_token(user.id, user.tenant_id, user.role.value)
    
    await log_action(db, user.id, user.tenant_id, "auth.login")
    
    from ...config import settings
    return TokenResponse(
        access_token=acc,
        refresh_token=ref,
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )

@router.post('/refresh', response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    from ...services.auth_service import verify_token
    payload = verify_token(refresh_token)
    
    import uuid
    user_id = uuid.UUID(payload.sub)
    tenant_id = uuid.UUID(payload.tenant_id)
    
    acc = create_access_token(user_id, tenant_id, payload.role)
    ref = create_refresh_token(user_id, tenant_id, payload.role)
    
    from ...config import settings
    return TokenResponse(
        access_token=acc,
        refresh_token=ref,
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )