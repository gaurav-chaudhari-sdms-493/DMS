"""A real, confirmed severe bug: cleanup_expired_trashed_items had no
tenant scoping at all — the "Empty Bin" API endpoint reused the same
function the scheduled worker task uses to sweep every tenant's expired
trash, so a single tenant's Empty Bin click deleted other tenants'
trashed items too. Confirmed live against the real account: an
unrelated tenant's folder was permanently deleted by a call meant to
only touch one tenant's own trash.

tenant_id=None must keep sweeping every tenant (the scheduled worker's
own use case, app/tasks/worker.py); a real tenant_id must scope both
the document and folder queries to that tenant only."""
import uuid
from datetime import datetime, timedelta

import pytest

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.folder import Folder
from app.services.document_service import cleanup_expired_trashed_items


async def _make_tenant_with_trashed_folder(db, folder_name):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"TrashScope Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email=f"trashscope_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    folder = Folder(
        id=uuid.uuid4(), tenant_id=tenant_id, name=folder_name,
        is_trashed=True, trashed_at=datetime.utcnow() - timedelta(days=60),
    )
    db.add_all([tenant, user, folder])
    await db.flush()
    return tenant_id, folder.id


@pytest.mark.asyncio
async def test_tenant_scoped_cleanup_only_deletes_the_given_tenant_folder():
    async with AsyncSessionLocal() as db:
        try:
            tenant_a, folder_a = await _make_tenant_with_trashed_folder(db, "Tenant A trash")
            tenant_b, folder_b = await _make_tenant_with_trashed_folder(db, "Tenant B trash")
            await db.commit()

            result = await cleanup_expired_trashed_items(db, retention_days=30, tenant_id=tenant_a)
            await db.commit()

            assert result["deleted_folders"] == 1

            res_a = await db.get(Folder, folder_a)
            res_b = await db.get(Folder, folder_b)
            assert res_a is None, "tenant A's own expired trashed folder must be purged"
            assert res_b is not None, "tenant B's folder must NOT be touched by tenant A's cleanup call"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_unscoped_cleanup_still_sweeps_every_tenant_for_the_worker_task():
    async with AsyncSessionLocal() as db:
        try:
            tenant_a, folder_a = await _make_tenant_with_trashed_folder(db, "Sweep A")
            tenant_b, folder_b = await _make_tenant_with_trashed_folder(db, "Sweep B")
            await db.commit()

            result = await cleanup_expired_trashed_items(db, retention_days=30, tenant_id=None)
            await db.commit()

            assert result["deleted_folders"] >= 2
            assert await db.get(Folder, folder_a) is None
            assert await db.get(Folder, folder_b) is None
        finally:
            await db.rollback()
            await db.close()
