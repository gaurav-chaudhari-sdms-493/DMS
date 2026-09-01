import base64
import httpx
from app.ai.base import VLMProvider


class OpenRouterVLMProvider(VLMProvider):
    """T22 — OpenRouter exposes an OpenAI-compatible chat/completions
    endpoint that accepts an image_url content part alongside text, so any
    OpenRouter-hosted vision model can be swapped in via openrouter_vlm_model
    without touching the extraction pipeline itself."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def extract_structured(self, image_bytes: bytes, prompt: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }
            ],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise Exception(f"OpenRouter VLM request failed with status {response.status_code}: {response.text}")

            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                error = data.get("error")
                raise Exception(f"OpenRouter VLM returned no choices (error={error})")

            text = (choices[0].get("message", {}) or {}).get("content", "")
            if not text or not text.strip():
                raise Exception("OpenRouter VLM returned an empty response")
            return text
