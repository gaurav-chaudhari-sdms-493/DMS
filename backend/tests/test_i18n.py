import pytest
import uuid
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.services.i18n_service import get_translations, SUPPORTED_LOCALES
from app.services.auth_service import hash_password, create_access_token


@pytest.mark.asyncio
async def test_get_translations_service_returns_seeded_rows():
    async with AsyncSessionLocal() as db:
        en = await get_translations(db, "en")
        mr = await get_translations(db, "mr")

    assert en["auth.login.title"] == "Sign in"
    assert mr["auth.login.title"] == "साइन इन करा"
    # Every English key has a Marathi counterpart — no partial rows.
    assert set(en.keys()) == set(mr.keys())
    assert len(en) > 0


@pytest.mark.asyncio
async def test_i18n_endpoint_returns_translations():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/i18n/en")
    assert res.status_code == 200
    body = res.json()
    assert body["common.save"] == "Save"


@pytest.mark.asyncio
async def test_i18n_endpoint_rejects_unsupported_locale():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/i18n/fr")
    assert res.status_code == 404
    assert "fr" not in SUPPORTED_LOCALES


@pytest.mark.asyncio
async def test_user_locale_defaults_to_en_and_is_patchable():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"i18n Tenant {uuid.uuid4().hex[:6]}")
            user = User(
                id=user_id, tenant_id=tenant_id,
                email=f"i18n_{uuid.uuid4().hex[:6]}@test.com",
                hashed_password=hash_password("testpassword123"),
                full_name="i18n Test User",
            )
            db.add_all([tenant, user])
            await db.commit()

            assert user.locale == "en"

            token = create_access_token(user_id, tenant_id, user.role)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.patch(
                    "/api/v1/auth/me/locale",
                    json={"locale": "mr"},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert res.status_code == 200
            assert res.json()["locale"] == "mr"

            await db.refresh(user)
            assert user.locale == "mr"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_update_locale_rejects_unsupported_value():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"i18n Tenant {uuid.uuid4().hex[:6]}")
            user = User(
                id=user_id, tenant_id=tenant_id,
                email=f"i18n_{uuid.uuid4().hex[:6]}@test.com",
                hashed_password=hash_password("testpassword123"),
                full_name="i18n Test User",
            )
            db.add_all([tenant, user])
            await db.commit()

            token = create_access_token(user_id, tenant_id, user.role)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.patch(
                    "/api/v1/auth/me/locale",
                    json={"locale": "fr"},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert res.status_code == 422
        finally:
            await db.rollback()
            await db.close()
