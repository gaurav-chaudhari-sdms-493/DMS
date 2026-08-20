from typing import List
import logging
from app.ai.base import RerankerProvider, RankedResult

logger = logging.getLogger(__name__)


class BGEM3RerankerProvider(RerankerProvider):
    """Local cross-encoder reranker (BGE) — no API key, no rate limit."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            logger.info("Loading local BGE reranker model (%s)...", self.model_name)
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
            logger.info("BGE reranker loaded successfully.")

    async def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[RankedResult]:
        if not documents:
            return []

        self._load_model()

        import asyncio
        import math
        from functools import partial

        pairs = [(query, doc) for doc in documents]
        loop = asyncio.get_running_loop()
        func = partial(self._model.predict, pairs, convert_to_numpy=True, show_progress_bar=False)
        raw_scores = await loop.run_in_executor(None, func)

        results = [
            RankedResult(index=i, score=1.0 / (1.0 + math.exp(-float(s))), text=documents[i])
            for i, s in enumerate(raw_scores)
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]
