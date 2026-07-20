import cohere
from typing import List
from app.ai.base import RerankerProvider, RankedResult

class CohereRerankerProvider(RerankerProvider):
    def __init__(self, api_key: str, model: str):
        # We use the v2 client asynchronously using run_in_executor in real scenario,
        # but cohere actually supports async now in v5: cohere.AsyncClient
        self.client = cohere.AsyncClient(api_key=api_key)
        self.model = model

    async def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[RankedResult]:
        if not documents:
            return []
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
