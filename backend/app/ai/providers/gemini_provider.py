import httpx
from typing import List
from app.ai.base import EmbeddingProvider
import logging

logger = logging.getLogger(__name__)

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        # Google Generative Language API uses batchEmbedContents for multiple inputs
        model_name = self.model if self.model.startswith("models/") else f"models/{self.model}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:batchEmbedContents?key={self.api_key}"
        
        # Prepare batch requests payload
        requests_payload = [
            {
                "model": model_name,
                "content": {
                    "parts": [{"text": t}]
                }
            }
            for t in texts
        ]
        payload = {"requests": requests_payload}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise Exception(f"Gemini Embedding request failed with status {response.status_code}: {response.text}")

            data = response.json()
            embeddings = [emb["values"] for emb in data.get("embeddings", [])]
            
            # Pad to 1024 dimensions to match pgvector db column definition
            padded_embeddings = []
            for emb in embeddings:
                if len(emb) < 1024:
                    emb = emb + [0.0] * (1024 - len(emb))
                elif len(emb) > 1024:
                    emb = emb[:1024]
                padded_embeddings.append(emb)
                
            return padded_embeddings

    @property
    def dimensions(self) -> int:
        return 1024
