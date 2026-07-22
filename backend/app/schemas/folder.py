from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[UUID] = None
    color: Optional[str] = "#1a73e8"


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_id: Optional[UUID] = None
    color: Optional[str] = None


class FolderResponse(BaseModel):
    id: UUID
    name: str
    parent_id: Optional[UUID] = None
    tenant_id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_starred: bool
    is_trashed: bool
    trashed_at: Optional[datetime] = None
    color: Optional[str] = "#1a73e8"

    class Config:
        from_attributes = True


class FolderTreeNode(BaseModel):
    id: UUID
    name: str
    parent_id: Optional[UUID] = None
    color: Optional[str] = "#1a73e8"
    subfolders: List["FolderTreeNode"] = []

    class Config:
        from_attributes = True


FolderTreeNode.model_rebuild()
