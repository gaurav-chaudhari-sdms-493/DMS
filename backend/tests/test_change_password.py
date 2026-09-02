"""Regression tests for change_password(), which had zero prior test
coverage. Real bug found live 2026-09-02: entering the same value for
current and new password was silently accepted -- no error, and the
password didn't meaningfully change."""
import uuid

import pytest
from fastapi import HTTPException

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import change_password, hash_password, verify_password


async def _make_user_with_password(db, password):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"ChangePw Tenant {uuid.uuid4().hex[:6]}")
    user = User(
        id=user_id, tenant_id=tenant_id, email=f"changepw_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=hash_password(password),
    )
    db.add_all([tenant, user])
    await db.flush()
    return user_id


@pytest.mark.asyncio
async def test_change_password_rejects_new_password_same_as_current():
    async with AsyncSessionLocal() as db:
        try:
            user_id = await _make_user_with_password(db, "OriginalPass123!")

            with pytest.raises(HTTPException) as exc_info:
                await change_password(user_id, "OriginalPass123!", "OriginalPass123!", db)
            assert exc_info.value.status_code == 400

            user = await db.get(User, user_id)
            assert verify_password("OriginalPass123!", user.hashed_password)
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current_password():
    async with AsyncSessionLocal() as db:
        try:
            user_id = await _make_user_with_password(db, "OriginalPass123!")

            with pytest.raises(HTTPException) as exc_info:
                await change_password(user_id, "WrongCurrentPassword!", "BrandNewPass456!", db)
            assert exc_info.value.status_code == 401
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_change_password_succeeds_with_a_genuinely_different_password():
    async with AsyncSessionLocal() as db:
        try:
            user_id = await _make_user_with_password(db, "OriginalPass123!")

            await change_password(user_id, "OriginalPass123!", "BrandNewPass456!", db)

            user = await db.get(User, user_id)
            assert verify_password("BrandNewPass456!", user.hashed_password)
            assert not verify_password("OriginalPass123!", user.hashed_password)
        finally:
            await db.rollback()
            await db.close()
