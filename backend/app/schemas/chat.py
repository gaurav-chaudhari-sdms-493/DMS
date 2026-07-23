from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.schemas.search import SearchResult

class ChatMessageSchema(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    results: Optional[List[SearchResult]] = None
    filters: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionSchema(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageSchema] = []

    class Config:
        from_attributes = True

class ChatSessionListItem(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True

class CreateSessionRequest(BaseModel):
    title: Optional[str] = None
    initial_query: Optional[str] = None

class SendMessageRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

class UpdateSessionRequest(BaseModel):
    title: str
