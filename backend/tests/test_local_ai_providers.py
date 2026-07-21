import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from app.ai.base import Message
from app.ai.providers.ollama_provider import OllamaLLMProvider, OllamaEmbeddingProvider
from app.ai.providers.bgem3_provider import BGEM3EmbeddingProvider
from app.ai.providers.bge_reranker_provider import BGERerankerProvider
from app.ocr.providers.pdfplumber_provider import PdfPlumberProvider
from app.ai.factory import get_llm_provider, get_embed_provider, get_rerank_provider
from app.ocr.factory import get_ocr_provider
from app.config import settings

class TestLocalAIProviders(unittest.IsolatedAsyncioTestCase):

    async def test_ollama_llm_provider_success(self):
        provider = OllamaLLMProvider(base_url="http://localhost:11434", model="llama3.3")
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Hello from local Ollama"}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            res = await provider.complete([Message(role="user", content="Hello")])
            self.assertEqual(res, "Hello from local Ollama")
            mock_post.assert_called_once()

    async def test_ollama_llm_provider_connect_error(self):
        provider = OllamaLLMProvider(base_url="http://localhost:11434", model="llama3.3")
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            with self.assertRaises(RuntimeError) as ctx:
                await provider.complete([Message(role="user", content="Hello")])
            self.assertIn("Ollama service unreachable", str(ctx.exception))

    async def test_ollama_embedding_provider_success(self):
        provider = OllamaEmbeddingProvider(base_url="http://localhost:11434", model="bge-m3", dim=1536)
        dummy_vector = [0.1] * 1024
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embeddings": [dummy_vector]}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            res = await provider.embed(["Sample document"])
            self.assertEqual(len(res), 1)
            self.assertEqual(len(res[0]), 1536)
            self.assertEqual(res[0][:1024], dummy_vector)

    async def test_bgem3_embedding_provider_mock(self):
        provider = BGEM3EmbeddingProvider(model_name="BAAI/bge-m3")
        mock_model = MagicMock()
        import numpy as np
        mock_model.encode.return_value = np.array([[0.5] * 1024])
        provider._model = mock_model

        res = await provider.embed(["Test text"])
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 1536)
        self.assertEqual(res[0][0], 0.5)
        self.assertEqual(res[0][1023], 0.5)
        self.assertEqual(res[0][1024], 0.0)  # Padded element

    async def test_bge_reranker_provider_mock(self):
        provider = BGERerankerProvider(model_name="BAAI/bge-reranker-v2-m3")
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.85, 0.22, 0.95]
        provider._model = mock_model

        docs = ["Doc 1", "Doc 2", "Doc 3"]
        results = await provider.rerank("query", docs, top_n=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].text, "Doc 3")
        self.assertEqual(results[0].score, 0.95)
        self.assertEqual(results[1].text, "Doc 1")
        self.assertEqual(results[1].score, 0.85)

    async def test_pdfplumber_ocr_provider(self):
        provider = PdfPlumberProvider()
        pages = await provider.extract_pages(b"Sample text file contents", "test.txt")
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["text"], "Sample text file contents")

    async def test_factory_instantiation(self):
        # Reset factory singletons
        import app.ai.factory as ai_factory
        import app.ocr.factory as ocr_factory
        ai_factory._llm_provider = None
        ai_factory._embed_provider = None
        ai_factory._rerank_provider = None
        ocr_factory._ocr_provider = None

        settings.ai_llm_provider = 'ollama'
        settings.ai_embed_provider = 'bgem3'
        settings.ai_rerank_provider = 'bge'
        settings.ai_ocr_provider = 'pdfplumber'

        llm = get_llm_provider()
        self.assertEqual(llm.__class__.__name__, 'OllamaLLMProvider')

        embed = get_embed_provider()
        self.assertEqual(embed.__class__.__name__, 'BGEM3EmbeddingProvider')

        rerank = get_rerank_provider()
        self.assertEqual(rerank.__class__.__name__, 'BGERerankerProvider')

        ocr = get_ocr_provider()
        self.assertEqual(ocr.__class__.__name__, 'PdfPlumberProvider')

if __name__ == "__main__":
    unittest.main()
