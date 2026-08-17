import cohere
import logging
from typing import List
from app.ai.base import RerankerProvider, EmbeddingProvider, RankedResult

logger = logging.getLogger(__name__)

class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "embed-english-v3.0"):
        self.api_key = api_key
        self.model = model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            client = cohere.AsyncClient(api_key=self.api_key)
            response = await client.embed(
                texts=texts,
                model=self.model,
                input_type="search_document"
            )
            return response.embeddings
        except Exception as e:
            logger.warning("Cohere embed failed or rate limited: %s. Returning zero fallback embeddings.", e)
            return [[0.0] * self.dimensions for _ in texts]

    @property
    def dimensions(self) -> int:
        return 1024

class CohereRerankerProvider(RerankerProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[RankedResult]:
        if not documents:
            return []
        try:
            client = cohere.AsyncClient(api_key=self.api_key)
            response = await client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_n
            )
            
            results = []
            for r in response.results:
                results.append(RankedResult(
                    index=r.index,
                    score=r.relevance_score,
                    text=documents[r.index]
                ))
            return results
        except Exception as e:
            logger.warning("Cohere rerank failed or rate limited: %s. Falling back to default RRF rank ordering.", e)
            return [
                RankedResult(index=i, score=0.85 - (i * 0.05), text=doc)
                for i, doc in enumerate(documents[:top_n])
            ]
