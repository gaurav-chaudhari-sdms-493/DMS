from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, Dict, List


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    title: str
    status: str
    created_at: datetime
    folder_id: Optional[UUID] = None


class BatchDocumentUploadResponse(BaseModel):
    documents: List[DocumentUploadResponse]
    total: int
    succeeded: int
    failed: int
    failures: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    folder_id: Optional[UUID] = None


class DocumentListItem(BaseModel):
    id: UUID
    title: str
    doc_type: Optional[str] = None
    status: str
    created_at: datetime
    folder_id: Optional[UUID] = None
    is_starred: bool = False
    is_trashed: bool = False
    trashed_at: Optional[datetime] = None
    file_size_bytes: int = 0
    current_version_id: Optional[UUID] = None
    s3_path: Optional[str] = None
    download_url: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    document_id: UUID
    title: str
    doc_type: Optional[str]
    status: str
    created_at: datetime
    folder_id: Optional[UUID] = None
    is_starred: bool = False
    is_trashed: bool = False
    trashed_at: Optional[datetime] = None
    current_version: Optional[Dict[str, Any]]
    metadata: List[Dict[str, Any]]
    versions: List[Dict[str, Any]]


class DriveStatsResponse(BaseModel):
    total_files: int
    total_folders: int
    total_size_bytes: int
    total_starred: int
    total_trashed: int
