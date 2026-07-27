from typing import List
from app.ai.base import EmbeddingProvider
import logging

logger = logging.getLogger(__name__)

class BGEM3EmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                logger.info(f"Loading local BGE-M3 embedding model ({self.model_name})...")
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info("Local BGE-M3 embedding model loaded successfully.")
            except ImportError as e:
                logger.error("sentence-transformers is not installed. Please install it using `pip install sentence-transformers`.")
                raise e
            except Exception as e:
                logger.error(f"Failed to load local BGE-M3 model: {e}")
                raise e

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        self._load_model()
        
        import asyncio
        from functools import partial
        
        loop = asyncio.get_running_loop()
        func = partial(self._model.encode, texts, convert_to_numpy=True, show_progress_bar=False)
        embeddings_np = await loop.run_in_executor(None, func)
        return embeddings_np.tolist()

    @property
    def dimensions(self) -> int:
        return 1024
