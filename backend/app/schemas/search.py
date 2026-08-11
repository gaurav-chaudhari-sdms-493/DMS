from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any, List

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    filters: Optional[dict] = None

class SearchResult(BaseModel):
    document_id: UUID
    document_name: str
    download_url: str
    page_number: Optional[int]
    snippet: str
    score: float
    metadata: dict

class SearchResponse(BaseModel):
    query: str
    ai_summary: str
    results: List[SearchResult]
    cached: bool = False
    took_ms: int
    search_mode: Optional[str] = "direct"
    hyde_triggered: Optional[bool] = False
