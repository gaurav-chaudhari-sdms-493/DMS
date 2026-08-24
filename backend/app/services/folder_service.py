from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from app.models.folder import Folder
from app.models.document import Document
from app.schemas.folder import FolderCreate, FolderUpdate, FolderResponse, FolderTreeNode
from app.services.audit_service import log_action


async def create_folder(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    folder_in: FolderCreate
) -> FolderResponse:
    if folder_in.parent_id:
        parent = await db.get(Folder, folder_in.parent_id)
        if not parent or parent.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent folder not found")

    folder = Folder(
        name=folder_in.name,
        parent_id=folder_in.parent_id,
        tenant_id=tenant_id,
        created_by=user_id,
        color=folder_in.color or "#1a73e8"
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)

    await log_action(db, user_id, tenant_id, "folder.create", resource_type="folder", resource_id=folder.id, details={"name": folder.name})

    return FolderResponse.model_validate(folder)


async def list_folders(
    db: AsyncSession,
    tenant_id: UUID,
    parent_id: Optional[UUID] = None,
    include_root: bool = False,
    is_starred: Optional[bool] = None,
    is_trashed: bool = False
) -> List[FolderResponse]:
    stmt = select(Folder).where(Folder.tenant_id == tenant_id, Folder.is_trashed == is_trashed)

    if is_starred is not None:
        stmt = stmt.where(Folder.is_starred == is_starred)
    elif not include_root and parent_id is not None:
        stmt = stmt.where(Folder.parent_id == parent_id)
    elif not include_root and parent_id is None and is_starred is None and not is_trashed:
        stmt = stmt.where(Folder.parent_id.is_(None))

    stmt = stmt.order_by(Folder.name.asc())
    res = await db.execute(stmt)
    folders = res.scalars().all()
    return [FolderResponse.model_validate(f) for f in folders]


async def get_folder(db: AsyncSession, folder_id: UUID, tenant_id: UUID) -> Folder:
    stmt = select(Folder).where(Folder.id == folder_id, Folder.tenant_id == tenant_id)
    res = await db.execute(stmt)
    folder = res.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


async def _is_descendant(db: AsyncSession, candidate_id: Optional[UUID], ancestor_id: UUID) -> bool:
    current = candidate_id
    for _ in range(100):
        if current is None:
            return False
        if current == ancestor_id:
            return True
        res = await db.execute(select(Folder.parent_id).where(Folder.id == current))
        row = res.first()
        if not row:
            return False
        current = row[0]
    return True


async def update_folder(
    db: AsyncSession,
    folder_id: UUID,
    tenant_id: UUID,
    folder_in: FolderUpdate,
    actor_id: UUID,
) -> FolderResponse:
    folder = await get_folder(db, folder_id, tenant_id)

    changes = {}
    if folder_in.parent_id is not None:
        if folder_in.parent_id == folder_id:
            raise HTTPException(status_code=400, detail="Folder cannot be its own parent")
        if await _is_descendant(db, folder_in.parent_id, folder_id):
            raise HTTPException(status_code=400, detail="Cannot move a folder into one of its own subfolders")
        parent = await db.get(Folder, folder_in.parent_id)
        if not parent or parent.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Target parent folder not found")
        folder.parent_id = folder_in.parent_id
        changes["parent_id"] = str(folder_in.parent_id)

    if folder_in.name is not None:
        folder.name = folder_in.name
        changes["name"] = folder_in.name
    if folder_in.color is not None:
        folder.color = folder_in.color
        changes["color"] = folder_in.color

    folder.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(folder)

    await log_action(db, actor_id, tenant_id, "folder.update", resource_type="folder", resource_id=folder.id, details=changes)

    return FolderResponse.model_validate(folder)


async def toggle_star_folder(db: AsyncSession, folder_id: UUID, tenant_id: UUID, actor_id: UUID) -> FolderResponse:
    folder = await get_folder(db, folder_id, tenant_id)
    folder.is_starred = not folder.is_starred
    folder.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(folder)

    await log_action(db, actor_id, tenant_id, "folder.star_toggle", resource_type="folder", resource_id=folder.id, details={"is_starred": folder.is_starred})

    return FolderResponse.model_validate(folder)


async def toggle_trash_folder(db: AsyncSession, folder_id: UUID, tenant_id: UUID, actor_id: UUID) -> FolderResponse:
    folder = await get_folder(db, folder_id, tenant_id)
    folder.is_trashed = not folder.is_trashed
    folder.trashed_at = datetime.utcnow() if folder.is_trashed else None
    folder.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(folder)

    await log_action(db, actor_id, tenant_id, "folder.trash_toggle", resource_type="folder", resource_id=folder.id, details={"is_trashed": folder.is_trashed})

    return FolderResponse.model_validate(folder)


async def delete_folder_permanently(db: AsyncSession, folder_id: UUID, tenant_id: UUID, actor_id: UUID) -> None:
    from app.services.document_service import delete_document_permanently

    folder = await db.get(Folder, folder_id)
    if not folder or folder.tenant_id != tenant_id:
        return

    folder_name = folder.name

    # 1. Delete all documents in this folder
    doc_stmt = select(Document.id).where(Document.folder_id == folder_id, Document.tenant_id == tenant_id)
    doc_res = await db.execute(doc_stmt)
    doc_ids = doc_res.scalars().all()
    for d_id in doc_ids:
        await delete_document_permanently(db, d_id, tenant_id, actor_id)

    # 2. Delete all subfolders recursively
    sub_stmt = select(Folder.id).where(Folder.parent_id == folder_id, Folder.tenant_id == tenant_id)
    sub_res = await db.execute(sub_stmt)
    sub_ids = sub_res.scalars().all()
    for s_id in sub_ids:
        await delete_folder_permanently(db, s_id, tenant_id, actor_id)

    await db.delete(folder)
    await db.commit()

    await log_action(db, actor_id, tenant_id, "folder.delete", resource_type="folder", resource_id=folder_id, details={"name": folder_name})


async def get_folder_tree(db: AsyncSession, tenant_id: UUID) -> List[FolderTreeNode]:
    stmt = select(Folder).where(Folder.tenant_id == tenant_id, Folder.is_trashed == False).order_by(Folder.name.asc())
    res = await db.execute(stmt)
    all_folders = res.scalars().all()

    nodes = {f.id: FolderTreeNode(id=f.id, name=f.name, parent_id=f.parent_id, color=f.color, subfolders=[]) for f in all_folders}
    roots: List[FolderTreeNode] = []

    for f in all_folders:
        node = nodes[f.id]
        if f.parent_id and f.parent_id in nodes:
            nodes[f.parent_id].subfolders.append(node)
        else:
            roots.append(node)

    return roots
