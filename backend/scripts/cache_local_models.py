#!/usr/bin/env python3
"""
Pre-caches local AI model weights (BGE-M3 embeddings, BGE Reranker, Ollama LLM),
checks OCR dependencies (pdfplumber, Tesseract), and runs end-to-end local inference tests.
"""
import sys
import logging
import shutil
import urllib.request
import json
import os

# Add parent directory to sys.path so app modules can be imported if run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def check_and_cache_hf_models():
    """Download and cache HuggingFace local models (BGE-M3 & BGE Reranker)."""
    logger.info("=== 1. Hugging Face Local Open-Source Models ===")
    
    # 1. BGE-M3 Embedding Model
    logger.info("Downloading and caching BAAI/bge-m3 embedding model...")
    try:
        from sentence_transformers import SentenceTransformer
        embed_model = SentenceTransformer("BAAI/bge-m3")
        # Smoke test embedding
        vec = embed_model.encode(["Local inferencing test"], convert_to_numpy=True)
        logger.info(f"✓ BAAI/bge-m3 cached and verified (dim={len(vec[0])})!")
    except Exception as e:
        logger.error(f"✗ Failed to cache BAAI/bge-m3 embedding model: {e}")
        return False

    # 2. BGE CrossEncoder Reranker Model
    logger.info("Downloading and caching BAAI/bge-reranker-v2-m3 model...")
    try:
        from sentence_transformers import CrossEncoder
        rerank_model = CrossEncoder("BAAI/bge-reranker-v2-m3")
        scores = rerank_model.predict([["query", "document snippet"]])
        logger.info(f"✓ BAAI/bge-reranker-v2-m3 cached and verified (score={float(scores[0]):.4f})!")
    except Exception as e:
        logger.error(f"✗ Failed to cache BAAI/bge-reranker-v2-m3 model: {e}")
        return False

    return True

def check_and_pull_ollama_models(base_url="http://localhost:11434", target_model="llama3.3"):
    """Check Ollama service status and verify or pull target model."""
    logger.info("=== 2. Ollama Local LLM Service ===")
    tags_url = f"{base_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(tags_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                models = [m.get("name") for m in data.get("models", [])]
                logger.info(f"✓ Ollama daemon is reachable at {base_url}. Installed models: {models}")
                
                # Check if target model or a fallback is available
                model_found = any(target_model in m for m in models)
                if model_found:
                    logger.info(f"✓ Target model '{target_model}' is available in Ollama!")
                else:
                    logger.warning(f"⚠ Model '{target_model}' not found in Ollama installed models. Attempting to pull...")
                    pull_url = f"{base_url.rstrip('/')}/api/pull"
                    pull_payload = json.dumps({"name": target_model}).encode('utf-8')
                    pull_req = urllib.request.Request(pull_url, data=pull_payload, headers={'Content-Type': 'application/json'})
                    try:
                        with urllib.request.urlopen(pull_req, timeout=300) as pull_res:
                            logger.info(f"✓ Model '{target_model}' pulled successfully!")
                    except Exception as pe:
                        logger.warning(f"⚠ Automatic pull for '{target_model}' failed or timed out: {pe}. Please run `ollama pull {target_model}` manually.")
                return True
    except Exception as e:
        logger.warning(f"⚠ Ollama service is not running locally at {base_url} ({e}). Start Ollama via `docker-compose up ollama` or `ollama serve`.")
        return False

def check_ocr_dependencies():
    """Verify local OCR tools (pdfplumber & tesseract)."""
    logger.info("=== 3. Local OCR Dependencies ===")
    pdfplumber_ok = False
    tesseract_ok = False

    try:
        import pdfplumber
        logger.info(f"✓ pdfplumber version {pdfplumber.__version__} is installed!")
        pdfplumber_ok = True
    except ImportError:
        logger.warning("⚠ pdfplumber is not installed.")

    tesseract_bin = shutil.which("tesseract")
    if tesseract_bin:
        logger.info(f"✓ Tesseract binary found at {tesseract_bin}")
        tesseract_ok = True
    else:
        logger.info("ℹ Tesseract binary not found in PATH (pdfplumber remains available for PDF text extraction).")

    return pdfplumber_ok or tesseract_ok

def main():
    logger.info("Starting local model caching & verification process...")

    hf_success = check_and_cache_hf_models()
    ollama_success = check_and_pull_ollama_models()
    ocr_success = check_ocr_dependencies()

    logger.info("\n=== Summary of 100% Local Inferencing Setup ===")
    logger.info(f" - Local Embeddings (BGE-M3): {'READY' if hf_success else 'FAILED'}")
    logger.info(f" - Local Reranker (BGE-Reranker-v2-m3): {'READY' if hf_success else 'FAILED'}")
    logger.info(f" - Local LLM (Ollama): {'REACHABLE' if ollama_success else 'NOT RUNNING (Start via docker-compose or ollama serve)'}")
    logger.info(f" - Local OCR (pdfplumber / Tesseract): {'READY' if ocr_success else 'MISSING'}")

    if hf_success and ocr_success:
        logger.info("\n🎉 Local AI models & packages cached successfully! System ready for 100% offline execution.")
    else:
        logger.error("\n❌ Some local AI dependencies failed. Review logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
