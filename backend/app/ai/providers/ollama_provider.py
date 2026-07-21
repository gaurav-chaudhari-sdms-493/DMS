import httpx
from typing import List
from app.ai.base import LLMProvider, EmbeddingProvider, Message
import logging

logger = logging.getLogger(__name__)

class OllamaLLMProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
            except httpx.ConnectError as e:
                logger.error(f"Cannot connect to Ollama service at {self.base_url}. Ensure Ollama service is running (e.g. `ollama serve` or docker container): {e}")
                raise RuntimeError(f"Ollama service unreachable at {self.base_url}: {e}") from e
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama returned HTTP status error {e.response.status_code}: {e.response.text}")
                raise e
            except httpx.HTTPError as e:
                logger.error(f"Ollama completion failed: {e}")
                raise e

class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "bge-m3", dim: int = 1536):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._dimensions = dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": texts
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    # Fallback for older Ollama versions using legacy /api/embeddings
                    embeddings = []
                    for text in texts:
                        legacy_url = f"{self.base_url}/api/embeddings"
                        legacy_payload = {"model": self.model, "prompt": text}
                        legacy_resp = await client.post(legacy_url, json=legacy_payload)
                        legacy_resp.raise_for_status()
                        embeddings.append(legacy_resp.json().get("embedding", []))
                else:
                    response.raise_for_status()
                    data = response.json()
                    embeddings = data.get("embeddings", [])
                
                # Pad/truncate to required dimensions if necessary (e.g. pgvector 1536)
                padded_embeddings = []
                for emb in embeddings:
                    if len(emb) < self._dimensions:
                        emb = emb + [0.0] * (self._dimensions - len(emb))
                    elif len(emb) > self._dimensions:
                        emb = emb[:self._dimensions]
                    padded_embeddings.append(emb)
                return padded_embeddings
            except httpx.ConnectError as e:
                logger.error(f"Cannot connect to Ollama service at {self.base_url}. Ensure Ollama service is running: {e}")
                raise RuntimeError(f"Ollama service unreachable at {self.base_url}: {e}") from e
            except httpx.HTTPError as e:
                logger.error(f"Ollama embedding failed: {e}")
                raise e

    @property
    def dimensions(self) -> int:
        return self._dimensions
