import pytest
import uuid
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.folder import Folder
from app.services.corpus_calibration_service import calibrate_corpus, get_calibration_status


async def _make_tenant_and_folder(db):
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"CalStatus Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=actor_id, tenant_id=tenant_id, email=f"calstatus_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    folder = Folder(id=uuid.uuid4(), tenant_id=tenant_id, name="CalStatus Corpus")
    db.add_all([tenant, user, folder])
    await db.flush()
    return tenant_id, actor_id, folder.id


@pytest.mark.asyncio
async def test_get_calibration_status_none_when_never_calibrated():
    """The workbench folder picker needs to show 'not calibrated' before a
    bulk-confirm submit, not only discover it via a 409 after the fact."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, _actor_id, folder_id = await _make_tenant_and_folder(db)
            status = await get_calibration_status(db, tenant_id, folder_id)
            assert status is None
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_get_calibration_status_reflects_real_calibration():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id = await _make_tenant_and_folder(db)
            await calibrate_corpus(db, tenant_id, folder_id, actor_id, sample_size=25, notes="batch review")
            await db.commit()

            status = await get_calibration_status(db, tenant_id, folder_id)
            assert status is not None
            assert status.calibrated_by_actor_id == actor_id
            assert status.sample_size == 25
            assert status.notes == "batch review"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_get_calibration_status_is_tenant_scoped():
    """A folder ID from tenant A must never report calibrated status
    sourced from a different tenant's row, even by ID collision."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id = await _make_tenant_and_folder(db)
            await calibrate_corpus(db, tenant_id, folder_id, actor_id, sample_size=5)
            await db.commit()

            other_tenant_id = uuid.uuid4()
            status = await get_calibration_status(db, other_tenant_id, folder_id)
            assert status is None
        finally:
            await db.rollback()
            await db.close()
