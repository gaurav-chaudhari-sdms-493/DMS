from typing import List
import logging
from app.ai.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingUnavailableError(RuntimeError):
    """Raised when no real embedding model is available."""


def _generate_fake_test_vector(text: str, dimensions: int = 1024) -> List[float]:
    """DEV/TEST ONLY — deterministic vector for testing without SentenceTransformer."""
    import hashlib
    import numpy as np
    seed = int.from_bytes(hashlib.sha256(text.encode('utf-8')).digest()[:4], 'big')
    rng = np.random.RandomState(seed)
    vec = rng.randn(dimensions)
    norm = np.linalg.norm(vec)
    return (vec / (norm if norm != 0 else 1.0)).tolist()


class BGEM3EmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-m3", allow_fake: bool = False):
        self.model_name = model_name
        self._dimensions = 1024
        self._model = None
        self._allow_fake = allow_fake

    def _load_model(self):
        if self._model is None:
            logger.info("Loading local BGE-M3 embedding model (%s)...", self.model_name)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info("BGE-M3 loaded successfully.")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        import asyncio
        from functools import partial

        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(None, self._load_model)
        except Exception as e:
            if self._allow_fake:
                logger.warning("Using FAKE deterministic vectors — test mode only")
                return [_generate_fake_test_vector(t, self._dimensions) for t in texts]
            raise EmbeddingUnavailableError(
                f"BGE-M3 embedding model unavailable: {e}. "
                "Install sentence-transformers, or set AI_EMBED_PROVIDER to a configured API provider."
            ) from e

        func = partial(self._model.encode, texts, convert_to_numpy=True, show_progress_bar=False)
        embeddings_np = await loop.run_in_executor(None, func)
        return embeddings_np.tolist()

    @property
    def dimensions(self) -> int:
        return self._dimensions
