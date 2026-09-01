from dataclasses import dataclass
from typing import List, Optional
import tiktoken

@dataclass
class Chunk:
    content: str
    page_number: int
    chunk_index: int
    token_count: int
    bbox: Optional[dict] = None

class TextChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64, model: str = 'gpt-4o-mini'):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Use gpt-4 or p50k_base if model not found
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def chunk_pages(self, pages: List[dict]) -> List[Chunk]:
        """Chunk extracted pages into token-limited overlapping chunks."""
        chunks = []
        global_index = 0
        
        for page in pages:
            if page.get("extraction_failed", False):
                continue
            text = page.get("text", "")
            if not text or not text.strip():
                continue
                
            tokens = self.tokenizer.encode(text)
            
            start = 0
            while start < len(tokens):
                end = start + self.chunk_size
                chunk_tokens = tokens[start:end]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                
                chunks.append(Chunk(
                    content=chunk_text,
                    page_number=page.get("page_number", 1),
                    chunk_index=global_index,
                    token_count=len(chunk_tokens),
                    bbox=page.get("bbox")
                ))
                
                global_index += 1
                if end >= len(tokens):
                    break
                start = end - self.chunk_overlap
                
        return chunks
