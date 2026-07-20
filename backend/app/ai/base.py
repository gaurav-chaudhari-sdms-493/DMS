from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Message:
    role: str  # 'system', 'user', 'assistant'
    content: str

@dataclass
class RankedResult:
    index: int
    score: float
    text: str

class LLMProvider(ABC):
    """Abstract interface for LLM completion providers."""
    
    @abstractmethod
    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        """Generate a completion from a list of messages."""
        ...

class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts, returning a list of float vectors."""
        ...
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimension."""
        ...

class RerankerProvider(ABC):
    """Abstract interface for reranker providers."""
    
    @abstractmethod
    async def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[RankedResult]:
        """Rerank documents given a query. Returns top_n results sorted by score desc."""
        ...

class OCRProvider(ABC):
    """Abstract interface for OCR/document parsing providers."""
    
    @abstractmethod
    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        """Extract text from document. Returns list of {page_number, text, bbox}. """
        ...
