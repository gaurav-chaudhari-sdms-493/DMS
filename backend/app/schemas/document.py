from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, Dict, List

class DocumentUploadResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    title: str
    status: str
    created_at: datetime

class BatchDocumentUploadResponse(BaseModel):
    documents: List[DocumentUploadResponse]
    total: int
    succeeded: int
    failed: int

class DocumentDetailResponse(BaseModel):
    document_id: UUID
    title: str
    doc_type: Optional[str]
    status: str
    created_at: datetime
    current_version: Optional[Dict[str, Any]]
    metadata: List[Dict[str, Any]]
    versions: List[Dict[str, Any]]


