from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.database import get_db
from app.deps import require_tenant_access, require_role
from app.schemas.auth import TokenPayload
from app.schemas.folder import FolderCreate, FolderUpdate, FolderResponse, FolderTreeNode
from app.services import folder_service, department_service

router = APIRouter(prefix="/folders", tags=["Folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_in: FolderCreate,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await folder_service.create_folder(db, tenant_id, user_id, folder_in)


@router.get("", response_model=List[FolderResponse])
async def list_folders(
    parent_id: Optional[uuid.UUID] = Query(None),
    include_root: bool = Query(False),
    is_starred: Optional[bool] = Query(None),
    is_trashed: bool = Query(False),
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    folders = await folder_service.list_folders(
        db=db,
        tenant_id=tenant_id,
        parent_id=parent_id,
        include_root=include_root,
        is_starred=is_starred,
        is_trashed=is_trashed
    )

    # T50: department-scoped personas only see projects (folders) their
    # department has been granted — "an RBAC group over projects, not a
    # container level." Tenant-wide roles (it_admin/auditor/legal_counsel)
    # are unaffected.
    if current_user.role in department_service.DEPARTMENT_SCOPED_ROLES:
        user_id = uuid.UUID(current_user.sub)
        granted = await department_service.list_user_department_folder_ids(db, tenant_id, user_id)
        folders = [f for f in folders if f.id in granted]

    return folders


@router.get("/tree", response_model=List[FolderTreeNode])
async def get_folder_tree(
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await folder_service.get_folder_tree(db, tenant_id)


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    folder = await folder_service.get_folder(db, folder_id, tenant_id, actor_id=user_id)
    return FolderResponse.model_validate(folder)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: uuid.UUID,
    folder_in: FolderUpdate,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await folder_service.update_folder(db, folder_id, tenant_id, folder_in, actor_id=user_id)


@router.post("/{folder_id}/star", response_model=FolderResponse)
async def toggle_star_folder(
    folder_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await folder_service.toggle_star_folder(db, folder_id, tenant_id, actor_id=user_id)


@router.post("/{folder_id}/trash", response_model=FolderResponse)
async def toggle_trash_folder(
    folder_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await folder_service.toggle_trash_folder(db, folder_id, tenant_id, actor_id=user_id)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder_permanently(
    folder_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'department_head', 'it_admin')),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    await folder_service.delete_folder_permanently(db, folder_id, tenant_id, actor_id=user_id)
