import cohere
from typing import List
from app.ai.base import RerankerProvider, EmbeddingProvider, RankedResult

class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "embed-english-v3.0"):
        self.client = cohere.AsyncClient(api_key=api_key)
        self.model = model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = await self.client.embed(
            texts=texts,
            model=self.model,
            input_type="search_document"
        )
        embeddings = response.embeddings
        
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
