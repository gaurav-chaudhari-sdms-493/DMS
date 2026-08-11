import pytest
import uuid
from app.services.auth_service import create_access_token, create_refresh_token, verify_token
from app.schemas.auth import TokenPayload
from app.models.user import UserRole


def test_auth_token_types():
    acc_token = create_access_token("user-123", "tenant-abc", UserRole.user)
    ref_token = create_refresh_token("user-123", "tenant-abc", UserRole.user)

    acc_payload = verify_token(acc_token)
    ref_payload = verify_token(ref_token)

    assert acc_payload.type == "access"
    assert ref_payload.type == "refresh"
    assert acc_payload.tenant_id == "tenant-abc"
    assert ref_payload.tenant_id == "tenant-abc"
    assert acc_payload.role == UserRole.user


def test_token_payload_schema():
    payload = TokenPayload(
        sub=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        role=UserRole.admin,
        exp=10000000000,
        jti=str(uuid.uuid4()),
        type="access"
    )
    assert payload.type == "access"
    assert payload.role == UserRole.admin
