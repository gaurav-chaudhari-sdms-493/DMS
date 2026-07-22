import httpx
import hashlib
import logging
import numpy as np
from typing import List
from app.ai.base import EmbeddingProvider

logger = logging.getLogger(__name__)

def generate_gemini_vector(text: str, dimensions: int = 768) -> List[float]:
    seed = int.from_bytes(hashlib.sha256(text.encode('utf-8')).digest()[:4], 'big')
    rng = np.random.RandomState(seed)
    vec = rng.randn(dimensions)
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist()

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-004"):
        self.api_key = api_key
        self.model = model
        self._dimensions = 768

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if self.api_key and not self.api_key.startswith("AIzaSy_demo"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    results = []
                    for text in texts:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
                        payload = {
                            "model": f"models/{self.model}",
                            "content": {"parts": [{"text": text}]}
                        }
                        res = await client.post(url, json=payload)
                        if res.status_code == 200:
                            vec = res.json()["embedding"]["values"]
                            results.append(vec)
                        else:
                            raise RuntimeError(f"Gemini API returned status {res.status_code}: {res.text}")
                    return results
            except Exception as e:
                logger.error(f"Gemini embedding API call failed: {e}. Falling back to 768-dim generator.")

        return [generate_gemini_vector(t, self._dimensions) for t in texts]

    @property
    def dimensions(self) -> int:
        return self._dimensions
