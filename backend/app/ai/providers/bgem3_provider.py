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
                import os
                import torch
                os.environ["TOKENIZERS_PARALLELISM"] = "false"
                torch.set_num_threads(1)
                from sentence_transformers import SentenceTransformer
                try:
                    self._model = SentenceTransformer(self.model_name, local_files_only=True)
                except Exception as e:
                    logger.info(f"Failed local load of '{self.model_name}', trying online download: {e}")
                    self._model = SentenceTransformer(self.model_name)
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
        embeddings_np = await asyncio.to_thread(self._model.encode, texts, convert_to_numpy=True)
        embeddings = embeddings_np.tolist()
        
        # Pad to 1536 dimensions to match pgvector db column definition
        padded_embeddings = []
        for emb in embeddings:
            if len(emb) < 1536:
                emb = emb + [0.0] * (1536 - len(emb))
            elif len(emb) > 1536:
                emb = emb[:1536]
            padded_embeddings.append(emb)
            
        return padded_embeddings

    @property
    def dimensions(self) -> int:
        return 1536
