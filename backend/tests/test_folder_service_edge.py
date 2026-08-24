import pytest
import uuid
from fastapi import HTTPException
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.services.folder_service import (
    create_folder,
    get_folder,
    update_folder,
    toggle_star_folder,
    toggle_trash_folder,
    delete_folder_permanently,
    get_folder_tree,
    _is_descendant
)
from app.schemas.folder import FolderCreate, FolderUpdate


@pytest.mark.asyncio
async def test_folder_cross_tenant_parent_rejection():
    """Verify creating or setting a parent folder belonging to another tenant fails with 404."""
    async with AsyncSessionLocal() as db:
        try:
            t1 = Tenant(id=uuid.uuid4(), name=f"Tenant1_{uuid.uuid4().hex[:6]}")
            t2 = Tenant(id=uuid.uuid4(), name=f"Tenant2_{uuid.uuid4().hex[:6]}")
            u1 = User(id=uuid.uuid4(), tenant_id=t1.id, email=f"u1_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            u2 = User(id=uuid.uuid4(), tenant_id=t2.id, email=f"u2_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([t1, t2, u1, u2])
            await db.commit()

            # Create parent folder in Tenant 1
            p_t1 = await create_folder(db, t1.id, u1.id, FolderCreate(name="Tenant1 Parent"))

            # Attempt to create folder in Tenant 2 pointing to Tenant 1 parent
            with pytest.raises(HTTPException) as exc_info:
                await create_folder(db, t2.id, u2.id, FolderCreate(name="Illegal Child", parent_id=p_t1.id))
            assert exc_info.value.status_code == 404
            assert "Parent folder not found" in exc_info.value.detail
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_folder_cycle_prevention():
    """Verify preventing moving a folder to be its own parent or moving into its own descendant."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Cycle Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"cycle_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            # Create hierarchy: Root -> Child -> Grandchild
            root = await create_folder(db, tenant_id, user_id, FolderCreate(name="Root"))
            child = await create_folder(db, tenant_id, user_id, FolderCreate(name="Child", parent_id=root.id))
            grandchild = await create_folder(db, tenant_id, user_id, FolderCreate(name="Grandchild", parent_id=child.id))

            # 1. Attempt to move Root to be its own parent
            with pytest.raises(HTTPException) as exc1:
                await update_folder(db, root.id, tenant_id, FolderUpdate(parent_id=root.id), actor_id=user_id)
            assert exc1.value.status_code == 400
            assert "own parent" in exc1.value.detail
            await db.rollback()

            # 2. Attempt to move Root into Grandchild (cycle detection)
            with pytest.raises(HTTPException) as exc2:
                await update_folder(db, root.id, tenant_id, FolderUpdate(parent_id=grandchild.id), actor_id=user_id)
            assert exc2.value.status_code == 400
            assert "subfolders" in exc2.value.detail
            await db.rollback()

            # Direct test on _is_descendant
            assert await _is_descendant(db, grandchild.id, root.id) is True
            assert await _is_descendant(db, root.id, grandchild.id) is False
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_folder_star_trash_and_tree():
    """Verify star, trash toggles, folder tree generation and permanent deletion."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Tree Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"tree_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            f1 = await create_folder(db, tenant_id, user_id, FolderCreate(name="Alpha"))
            f2 = await create_folder(db, tenant_id, user_id, FolderCreate(name="Beta", parent_id=f1.id))

            # Toggle star
            starred = await toggle_star_folder(db, f1.id, tenant_id, actor_id=user_id)
            assert starred.is_starred is True

            # Check tree
            tree = await get_folder_tree(db, tenant_id)
            assert len(tree) == 1
            assert tree[0].name == "Alpha"
            assert len(tree[0].subfolders) == 1
            assert tree[0].subfolders[0].name == "Beta"

            # Toggle trash
            trashed = await toggle_trash_folder(db, f2.id, tenant_id, actor_id=user_id)
            assert trashed.is_trashed is True

            # Trashed folder excluded from tree
            tree_after_trash = await get_folder_tree(db, tenant_id)
            assert len(tree_after_trash[0].subfolders) == 0

            # Permanent deletion
            await delete_folder_permanently(db, f2.id, tenant_id, actor_id=user_id)
            with pytest.raises(HTTPException) as exc:
                await get_folder(db, f2.id, tenant_id)
            assert exc.value.status_code == 404
        finally:
            await db.rollback()
            await db.close()
