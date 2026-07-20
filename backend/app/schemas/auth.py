from pydantic import BaseModel, EmailStr
from uuid import UUID

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int

class TokenPayload(BaseModel):
    sub: str  # user_id
    tenant_id: str
    role: str
    exp: int
    jti: str  # JWT ID for refresh token tracking
