import asyncio
from functools import partial
from typing import List
from app.ai.base import RerankerProvider, RankedResult
import logging

logger = logging.getLogger(__name__)

class BGERerankerProvider(RerankerProvider):
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                import os
                import torch
                os.environ["TOKENIZERS_PARALLELISM"] = "false"
                torch.set_num_threads(1)
                from sentence_transformers import CrossEncoder
                try:
                    self._model = CrossEncoder(self.model_name, local_files_only=True)
                except Exception as e:
                    logger.info(f"Failed local load of '{self.model_name}', trying online download: {e}")
                    self._model = CrossEncoder(self.model_name)
            except ImportError as e:
                logger.error("sentence-transformers is not installed. Please run `pip install sentence-transformers`.")
                raise e
            except Exception as e:
                logger.error(f"Failed to load local BGE reranker model '{self.model_name}': {e}")
                raise e

    async def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[RankedResult]:
        if not documents:
            return []

        self._load_model()

        pairs = [[query, doc] for doc in documents]
        
        import asyncio
        scores = await asyncio.to_thread(self._model.predict, pairs)
        
        # Combine index, score, and document text
        import math
        def sigmoid(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-x))

        results = [
            RankedResult(index=i, score=float(sigmoid(float(score))), text=documents[i])
            for i, score in enumerate(scores)
        ]
        
        # Sort by relevance score descending and return top_n
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]
