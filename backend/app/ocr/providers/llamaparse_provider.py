import httpx
import asyncio
from typing import List
from app.ai.base import OCRProvider

class LlamaParseProvider(OCRProvider):
    """
    LlamaParse Integration. 
    Production-ready stub that uploads to Cloud LlamaIndex, polls, and returns parsed text.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cloud.llamaindex.ai/api/parsing"
        
    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            files = {"file": (filename, file_bytes)}
            # 1. Upload
            resp = await client.post(f"{self.base_url}/upload", headers=headers, files=files)
            resp.raise_for_status()
            job_id = resp.json().get("id")
            
            # 2. Poll status
            for _ in range(60):
                status_resp = await client.get(f"{self.base_url}/job/{job_id}", headers=headers)
                status_resp.raise_for_status()
                status_data = status_resp.json()
                if status_data.get("status") == "SUCCESS":
                    break
                elif status_data.get("status") == "ERROR":
                    raise Exception(f"LlamaParse error: {status_data}")
                await asyncio.sleep(2)
            
            # 3. Get results (mocking page splitting based on result)
            res_resp = await client.get(f"{self.base_url}/job/{job_id}/result/markdown", headers=headers)
            res_resp.raise_for_status()
            text = res_resp.json().get("markdown", "")
            
        return [{
            "page_number": 1,
            "text": text.strip() if text else "",
            "words": [],
            "bbox": {},
            "extraction_failed": not bool(text and text.strip())
        }]
