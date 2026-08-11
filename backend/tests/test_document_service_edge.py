import pytest
import uuid
from io import BytesIO
from fastapi import HTTPException, UploadFile
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.folder import Folder
from app.services.document_service import upload_document, upload_documents_bulk
from app.config import settings


@pytest.mark.asyncio
async def test_document_upload_file_size_exceeded():
    """Verify uploading a file exceeding max_upload_size_mb raises 413 Payload Too Large."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Doc Size Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"docsize_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            overflow_size = (settings.max_upload_size_mb * 1024 * 1024) + 1024
            file_obj = UploadFile(filename="huge_file.pdf", file=BytesIO(b"0" * overflow_size))

            with pytest.raises(HTTPException) as exc_info:
                await upload_document(file_obj, tenant_id, user_id, db)
            assert exc_info.value.status_code == 413
            assert f"File exceeds the {settings.max_upload_size_mb} MB limit" in exc_info.value.detail
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_document_upload_disallowed_extension():
    """Verify uploading a file with disallowed extension raises 400 Bad Request."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Doc Ext Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"docext_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            file_obj = UploadFile(filename="malicious.exe", file=BytesIO(b"echo 'malicious script'"))

            with pytest.raises(HTTPException) as exc_info:
                await upload_document(file_obj, tenant_id, user_id, db)
            assert exc_info.value.status_code == 400
            assert "File type '.exe' is not supported" in exc_info.value.detail
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_document_bulk_upload_partial_failures():
    """Verify bulk upload handles invalid files and reports failure metadata."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Bulk Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"bulk_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            files = [
                UploadFile(filename="script.sh", file=BytesIO(b"#!/bin/bash\nrm -rf /")),
                UploadFile(filename="virus.exe", file=BytesIO(b"malware")),
            ]

            resp = await upload_documents_bulk(files, tenant_id, user_id, db)
            assert resp.total == 2
            assert resp.failed == 2
            assert len(resp.failures) == 2
            assert resp.failures[0]["filename"] == "script.sh"
            assert "not supported" in resp.failures[0]["error"]
            assert resp.failures[1]["filename"] == "virus.exe"
            assert "not supported" in resp.failures[1]["error"]
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_document_cross_tenant_folder_assignment():
    """Verify uploading a document to a folder owned by another tenant fails with 404."""
    async with AsyncSessionLocal() as db:
        try:
            t1 = Tenant(id=uuid.uuid4(), name=f"Doc T1 {uuid.uuid4().hex[:6]}")
            t2 = Tenant(id=uuid.uuid4(), name=f"Doc T2 {uuid.uuid4().hex[:6]}")
            u1 = User(id=uuid.uuid4(), tenant_id=t1.id, email=f"u1_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            u2 = User(id=uuid.uuid4(), tenant_id=t2.id, email=f"u2_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([t1, t2, u1, u2])
            await db.commit()

            # Folder owned by Tenant 1
            f1 = Folder(id=uuid.uuid4(), name="T1 Folder", tenant_id=t1.id, created_by=u1.id)
            db.add(f1)
            await db.commit()

            # Tenant 2 user attempts uploading to Tenant 1 folder
            file_obj = UploadFile(filename="test.pdf", file=BytesIO(b"PDF Content"))
            with pytest.raises(HTTPException) as exc_info:
                await upload_document(file_obj, t2.id, u2.id, db, folder_id=f1.id)
            assert exc_info.value.status_code == 404
            assert "Target folder not found" in exc_info.value.detail
        finally:
            await db.rollback()
            await db.close()
