import base64
import httpx
from typing import List
from app.ai.base import EmbeddingProvider, VLMProvider
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


class GeminiVLMProvider(VLMProvider):
    """T22 — Gemini's generateContent endpoint accepts an inline image part
    alongside text, which is what lets one call both read a scanned register
    page and report where on the page it read each field from."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def extract_structured(self, image_bytes: bytes, prompt: str) -> str:
        model_name = self.model if self.model.startswith("models/") else f"models/{self.model}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(image_bytes).decode("ascii")}},
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise Exception(f"Gemini VLM request failed with status {response.status_code}: {response.text}")

            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                block_reason = data.get("promptFeedback", {}).get("blockReason")
                raise Exception(f"Gemini VLM returned no candidates (blockReason={block_reason})")

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            if not text.strip():
                raise Exception("Gemini VLM returned an empty response")
            return text
