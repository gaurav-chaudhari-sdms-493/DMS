import cohere
from typing import List
from app.ai.base import RerankerProvider, EmbeddingProvider, RankedResult

class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "embed-english-v3.0"):
        self.api_key = api_key
        self.model = model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = cohere.AsyncClient(api_key=self.api_key)
        response = await client.embed(
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
        self.api_key = api_key
        self.model = model

    async def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[RankedResult]:
        if not documents:
            return []
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
