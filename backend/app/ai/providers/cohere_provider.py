import cohere
import logging
from typing import List
from app.ai.base import RerankerProvider, RankedResult

logger = logging.getLogger(__name__)

class CohereRerankerProvider(RerankerProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.client = cohere.AsyncClient(api_key=api_key) if api_key and api_key != "your_cohere_api_key" else None

    async def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[RankedResult]:
        if not documents:
            return []
        
        if not self.client:
            logger.warning("Cohere API key not configured. Returning top RRF candidates without reranking.")
            return [RankedResult(index=i, score=1.0 - (i * 0.05), text=d) for i, d in enumerate(documents[:top_n])]
        
        try:
            response = await self.client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_n
            )
            results = []
            for r in response.results:
                results.append(RankedResult(index=r.index, score=r.relevance_score, text=documents[r.index]))
            return results
        except Exception as e:
            logger.error(f"Cohere rerank API call failed: {e}. Falling back to default candidates order.")
            return [RankedResult(index=i, score=1.0 - (i * 0.05), text=d) for i, d in enumerate(documents[:top_n])]
