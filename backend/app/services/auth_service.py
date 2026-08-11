import time
import uuid
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.schemas.auth import TokenPayload, SignUpRequest, SignUpResponse
from app.models.user import User, UserRole
from app.models.tenant import Tenant

import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

async def sign_up(body: SignUpRequest, db: AsyncSession) -> SignUpResponse:
    """Creates a new tenant and an admin user."""
    stmt = select(User).where(User.email == body.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create tenant
    tenant = Tenant(name=f"{body.full_name}'s Organization")
    db.add(tenant)
    await db.flush()

    # Create user
    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        tenant_id=tenant.id,
        role=UserRole.admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    acc = create_access_token(user.id, tenant.id, user.role.value)
    ref = create_refresh_token(user.id, tenant.id, user.role.value)

    return SignUpResponse(
        user_id=user.id,
        tenant_id=tenant.id,
        full_name=user.full_name,
        email=user.email,
        access_token=acc,
        refresh_token=ref,
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )

def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    exp = int(time.time()) + (settings.jwt_access_token_expire_minutes * 60)
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "type": "access"
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    exp = int(time.time()) + (settings.jwt_refresh_token_expire_days * 86400)
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "type": "refresh"
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_password_reset_token(email: str) -> str:
    exp = int(time.time()) + (15 * 60)
    to_encode = {
        "sub": email,
        "type": "reset_password",
        "exp": exp,
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

async def reset_password_with_token(email: str, token: str, new_password: str, db: AsyncSession) -> bool:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "reset_password" or payload.get("sub") != email:
            raise HTTPException(status_code=400, detail="Invalid password reset token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=444, detail="User not found")

    user.hashed_password = hash_password(new_password)
    await db.commit()
    return True

def verify_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )