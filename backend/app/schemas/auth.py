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
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = 'bearer'
    expires_in: int | None = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenPayload(BaseModel):
    sub: str  # user_id
    tenant_id: str
    role: str
    exp: int
    jti: str  # JWT ID for refresh token tracking
    type: str = "access"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str = Field(..., min_length=8)

class FileTypeCount(BaseModel):
    extension: str
    count: int
    size_bytes: int

class UserProfileResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    role: str
    locale: str
    tenant_id: UUID
    tenant_name: str
    created_at: str
    total_files: int
    total_folders: int
    total_size_bytes: int
    total_chunks: int
    file_types_breakdown: list[FileTypeCount]


class UpdateLocaleRequest(BaseModel):
    locale: str = Field(..., pattern="^(en|mr)$")


class UpdateLocaleResponse(BaseModel):
    locale: str