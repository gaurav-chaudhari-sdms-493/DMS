import base64
import json
import uuid
from datetime import datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.models.license import License
from app.services import license_service


async def _make_tenant(db):
    tenant = Tenant(id=uuid.uuid4(), name=f"License Test {uuid.uuid4().hex[:6]}")
    db.add(tenant)
    await db.flush()
    return tenant


@pytest.mark.asyncio
async def test_fresh_tenant_gets_trial_and_is_allowed():
    async with AsyncSessionLocal() as db:
        tenant = await _make_tenant(db)
        result = await license_service.check_saas_capacity(db, tenant.id)
        await db.commit()
        assert result.allowed is True
        assert result.status == "trialing"
        assert result.plan_key == "trial"
        assert result.documents_used == 0


@pytest.mark.asyncio
async def test_document_limit_breach_blocks_and_reports_reason():
    async with AsyncSessionLocal() as db:
        tenant = await _make_tenant(db)
        sub = await license_service.get_or_create_subscription(db, tenant.id)
        sub.plan_key = "trial"
        await db.commit()

        original_limit = license_service.PLAN_DEFINITIONS["trial"]["max_documents"]
        license_service.PLAN_DEFINITIONS["trial"]["max_documents"] = 0
        try:
            result = await license_service.check_saas_capacity(db, tenant.id)
        finally:
            license_service.PLAN_DEFINITIONS["trial"]["max_documents"] = original_limit

        assert result.allowed is False
        assert "limit reached" in result.reason
        assert "readable and exportable" in result.reason


@pytest.mark.asyncio
async def test_expired_trial_blocks_upload():
    async with AsyncSessionLocal() as db:
        tenant = await _make_tenant(db)
        sub = await license_service.get_or_create_subscription(db, tenant.id)
        sub.trial_ends_at = datetime.utcnow() - timedelta(days=1)
        await db.commit()

        result = await license_service.check_saas_capacity(db, tenant.id)
        assert result.allowed is False
        assert result.status == "expired"
        assert "Trial expired" in result.reason


@pytest.mark.asyncio
async def test_active_subscription_ignores_trial_expiry():
    async with AsyncSessionLocal() as db:
        tenant = await _make_tenant(db)
        sub = await license_service.get_or_create_subscription(db, tenant.id)
        sub.status = "active"
        sub.plan_key = "enterprise"
        sub.trial_ends_at = datetime.utcnow() - timedelta(days=100)
        await db.commit()

        result = await license_service.check_saas_capacity(db, tenant.id)
        assert result.allowed is True
        assert result.documents_limit is None  # enterprise = unlimited


def test_valid_signature_verifies():
    priv = Ed25519PrivateKey.generate()
    pub_b64 = base64.b64encode(priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    payload = {"a": 1, "b": "two"}
    sig = priv.sign(license_service._canonical_payload_bytes(payload))
    sig_b64 = base64.b64encode(sig).decode()

    original = license_service.VENDOR_PUBLIC_KEY_B64
    license_service.VENDOR_PUBLIC_KEY_B64 = pub_b64
    try:
        is_valid, reason = license_service.verify_license_signature(payload, sig_b64)
    finally:
        license_service.VENDOR_PUBLIC_KEY_B64 = original
    assert is_valid is True
    assert reason is None


def test_tampered_payload_fails_verification():
    priv = Ed25519PrivateKey.generate()
    pub_b64 = base64.b64encode(priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    payload = {"max_nodes": 1}
    sig = priv.sign(license_service._canonical_payload_bytes(payload))
    sig_b64 = base64.b64encode(sig).decode()

    tampered_payload = {"max_nodes": 999}  # signed for 1, claiming 999

    original = license_service.VENDOR_PUBLIC_KEY_B64
    license_service.VENDOR_PUBLIC_KEY_B64 = pub_b64
    try:
        is_valid, reason = license_service.verify_license_signature(tampered_payload, sig_b64)
    finally:
        license_service.VENDOR_PUBLIC_KEY_B64 = original
    assert is_valid is False
    assert "altered" in reason


@pytest.mark.asyncio
async def test_onprem_no_license_installed_blocks(monkeypatch):
    # billing_dg_license is deployment-wide, not per-test-isolated, so patch
    # the lookup directly rather than depend on the shared dev DB being empty.
    async def _no_license(db):
        return None
    monkeypatch.setattr(license_service, "get_installed_license", _no_license)

    async with AsyncSessionLocal() as db:
        result = await license_service.check_onprem_capacity(db)
        assert result.allowed is False
        assert result.status == "blocked"
        assert "No license installed" in result.reason


@pytest.mark.asyncio
async def test_onprem_valid_license_allows_upload():
    priv = Ed25519PrivateKey.generate()
    pub_b64 = base64.b64encode(priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()

    payload = {
        "license_id": str(uuid.uuid4()),
        "customer_name": "Test Waqf Board",
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z",
        "max_nodes": 3,
        "max_gpu_count": 1,
        "plan_key": "on_prem_standard",
    }
    sig = priv.sign(license_service._canonical_payload_bytes(payload))
    envelope = json.dumps({"payload": payload, "signature_b64": base64.b64encode(sig).decode()}).encode()

    original = license_service.VENDOR_PUBLIC_KEY_B64
    license_service.VENDOR_PUBLIC_KEY_B64 = pub_b64
    try:
        async with AsyncSessionLocal() as db:
            lic = await license_service.install_license(db, envelope, None)
            assert lic.is_valid is True
            result = await license_service.check_onprem_capacity(db)
            assert result.allowed is True
            assert result.status == "active"
    finally:
        license_service.VENDOR_PUBLIC_KEY_B64 = original


@pytest.mark.asyncio
async def test_onprem_tampered_license_rejected_at_install():
    priv = Ed25519PrivateKey.generate()
    pub_b64 = base64.b64encode(priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()

    payload = {"customer_name": "Honest Corp", "max_nodes": 1, "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"}
    sig = priv.sign(license_service._canonical_payload_bytes(payload))

    tampered_payload = dict(payload)
    tampered_payload["max_nodes"] = 9999  # attacker bumps capacity post-signing
    envelope = json.dumps({"payload": tampered_payload, "signature_b64": base64.b64encode(sig).decode()}).encode()

    original = license_service.VENDOR_PUBLIC_KEY_B64
    license_service.VENDOR_PUBLIC_KEY_B64 = pub_b64
    try:
        async with AsyncSessionLocal() as db:
            lic = await license_service.install_license(db, envelope, None)
            assert lic.is_valid is False
            assert "altered" in lic.invalid_reason
    finally:
        license_service.VENDOR_PUBLIC_KEY_B64 = original
