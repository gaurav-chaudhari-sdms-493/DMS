# Known Limitations & System Boundaries

This document outlines the current technical boundaries, operational assumptions, and architectural constraints of the Multi-Tenant Document Management System (DMS).

---

## 1. Document Extraction & OCR
- **Scanned Images**: Text extraction from low-resolution or handwritten scanned images relies on Tesseract OCR / `pdfplumber`. If OCR fails, the system marks the document status as `failed` rather than embedding placeholder text.
- **Maximum File Size**: Single file uploads are capped at **50 MB** per document.
- **Supported Formats**: `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`, `.csv`, `.txt`, `.md`, `.rtf`, `.json`, `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`.

---

## 2. Embedding & Vector Search
- **Embedding Provider**: Default local embedding provider uses BGE-M3 (`BAAI/bge-m3`, 1024 dimensions). It requires `sentence-transformers` installed locally. If missing, `EmbeddingUnavailableError` is raised unless `allow_fake=True` is explicitly passed in unit tests.
- **Vector Search Engine**: PostgreSQL `pgvector` with HNSW cosine similarity index.

---

## 3. Asynchronous Processing & Celery
- **Task Execution**: Document parsing and vector indexing are offloaded to Celery background workers via Redis. Real-time document availability is subject to background queue processing latency.
- **Polling / WebSockets**: The frontend periodically polls document status (`pending` -> `indexed` / `failed`) or updates status upon page refreshes.

---

## 4. Multi-Tenant Row Level Security (RLS)
- **Database Policies**: Enforced at the PostgreSQL connection level via `SET LOCAL app.current_tenant_id = '...'`.
- **Session Scoping**: SQLAlchemy database sessions set session-scoped tenant context (`false` as 3rd arg) to preserve tenant boundaries across internal transaction commits within a request.
