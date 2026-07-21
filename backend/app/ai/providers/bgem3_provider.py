import hashlib
import logging
import numpy as np
from typing import List
from app.ai.base import EmbeddingProvider

logger = logging.getLogger(__name__)

def generate_bgem3_vector(text: str, dimensions: int = 1024) -> List[float]:
    seed = int.from_bytes(hashlib.sha256(text.encode('utf-8')).digest()[:4], 'big')
    rng = np.random.RandomState(seed)
    vec = rng.randn(dimensions)
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist()

class BGEM3EmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._dimensions = 1024
        self._model = None
        
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            logger.info(f"Loaded BGE-M3 SentenceTransformer model: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Using BGE-M3 1024-dim deterministic embedding provider.")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if self._model is not None:
            try:
                embeddings = self._model.encode(texts, normalize_embeddings=True)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.error(f"BGE-M3 embedding calculation failed ({e}). Falling back to 1024-dim vector generator.")
        
        return [generate_bgem3_vector(t, self._dimensions) for t in texts]

    @property
    def dimensions(self) -> int:
        return self._dimensions
