from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignUpRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class SignUpResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    full_name: str
    email: EmailStr

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