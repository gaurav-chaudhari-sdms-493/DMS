import cohere
import hashlib
import logging
import numpy as np
from typing import List
from app.ai.base import EmbeddingProvider

logger = logging.getLogger(__name__)

class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, target_dimensions: int = 1024, model: str = "embed-english-v3.0"):
        self.api_key = api_key
        self.model = model
        self._target_dimensions = target_dimensions
        self.client = cohere.AsyncClient(api_key=api_key) if api_key and api_key != "your_cohere_api_key" else None

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if self.client:
            try:
                response = await self.client.embed(
                    texts=texts,
                    model=self.model,
                    input_type="search_document"
                )
                embeddings = []
                for emb in response.embeddings:
                    # Adjust dimension to target_dimensions (1024 or 768) if needed
                    vec = list(emb)
                    if len(vec) < self._target_dimensions:
                        vec.extend([0.0] * (self._target_dimensions - len(vec)))
                    elif len(vec) > self._target_dimensions:
                        vec = vec[:self._target_dimensions]
                    embeddings.append(vec)
                return embeddings
            except Exception as e:
                logger.error(f"Cohere embedding fallback API call failed: {e}")

        # Deterministic fallback vector if Cohere API key is invalid/unconfigured
        results = []
        for text in texts:
            seed = int.from_bytes(hashlib.sha256(text.encode('utf-8')).digest()[:4], 'big')
            rng = np.random.RandomState(seed)
            vec = rng.randn(self._target_dimensions)
            norm = np.linalg.norm(vec)
            results.append((vec / norm).tolist())
        return results

    @property
    def dimensions(self) -> int:
        return self._target_dimensions
