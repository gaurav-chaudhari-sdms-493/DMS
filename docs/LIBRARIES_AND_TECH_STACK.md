# Tech Stack & Dependencies Reference

## 1. System Architecture Technology Summary

The DMS platform relies on open-source frameworks, high-performance database engines, and AI software development kits.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND APPLICATION                          │
│     Next.js 14 (App Router) │ React 18 │ TypeScript │ Tailwind CSS    │
│     Lucide React (Icons)   │ Mammoth.js (.docx) │ XLSX (Spreadsheets)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST API (JWT)
┌───────────────────────────────────▼────────────────────────────────────┐
│                           BACKEND APPLICATION                          │
│     FastAPI 0.115 │ Uvicorn (ASGI) │ AsyncIO │ Pydantic v2            │
│     SQLAlchemy 2.0 (Async) │ AsyncPG │ Alembic Migrations          │
│     SlowAPI (Rate Limit)   │ PyJWT / Passlib (Bcrypt Security)         │
└───────┬───────────────────────────┬───────────────────────────┬────────┘
        │ Task Dispatch             │ Relational & Vectors      │ S3 API
┌───────▼──────────┐        ┌───────▼──────────┐        ┌───────▼──────────┐
│  REDIS & CELERY  │        │   POSTGRESQL     │        │   OBJECT STORE   │
│ Redis 7 (Broker) │        │ PostgreSQL 16    │        │ MinIO (Local)    │
│ Celery 5.4Worker │        │ pgvector 0.3.2   │        │ AWS S3 (Prod)    │
│ Flower Dashboard │        │ (HNSW Indexing)  │        │ Boto3 SDK        │
└──────────────────┘        └──────────────────┘        └──────────────────┘
```

---

## 2. Backend Dependencies (Python)

All backend Python packages are defined in `backend/requirements.txt`:

| Library / Package | Version | Purpose & Usage in DMS |
|-------------------|---------|------------------------|
| **`fastapi`** | `0.115.0` | High-performance async web framework powering REST APIs, routing, dependency injection, and automatic OpenAPI spec generation (`/api/docs`). |
| **`uvicorn[standard]`** | `0.30.6` | Lightning-fast ASGI server implementation hosting FastAPI applications. |
| **`sqlalchemy[asyncio]`** | `2.0.35` | Modern Python ORM providing async database connectivity, session management, and model definitions. |
| **`asyncpg`** | `0.29.0` | Asynchronous PostgreSQL database driver optimized for high-throughput async query performance. |
| **`pgvector`** | `0.3.2` | Python bindings for PostgreSQL `pgvector` extension; handles vector embedding columns (`Vector(1024)`) and HNSW distance operators (`<->`, `<=>`). |
| **`alembic`** | `1.13.2` | Database migration framework for schema evolution, column alterations, and index creation. |
| **`pydantic`** | `2.9.2` | Data validation, serialisation, and request/response schema enforcement. |
| **`pydantic-settings`** | `2.5.2` | Type-safe environment variable parser parsing `.env` files into application settings. |
| **`redis`** | `5.1.1` | Redis client handling Layer-0 semantic search caching and session cache key management. |
| **`celery`** | `5.4.0` | Distributed asynchronous task queue executing background document ingestion, text parsing, dynamic metadata extraction, and vectorization. |
| **`flower`** | `2.0.1` | Real-time web dashboard (Port `5555`) for monitoring Celery task execution, worker state, task latency, and failure retries. |
| **`boto3`** | `1.35.0` | AWS SDK for Python used for uploading, downloading, and generating pre-signed URLs for MinIO / AWS S3 objects. |
| **`botocore`** | `1.35.0` | Core low-level HTTP transport layer for AWS S3 service integration. |
| **`openai`** | `1.51.0` | Official OpenAI SDK used for `gpt-4o-mini`, `gpt-4o`, and `text-embedding-3-small` API calls. |
| **`anthropic`** | `0.34.2` | Official Anthropic SDK for Claude LLM models (`claude-3-5-haiku`, `claude-3-5-sonnet`). |
| **`cohere`** | `5.9.1` | Cohere API client providing cross-encoder re-ranking (`rerank-english-v3.0`). |
| **`pdfplumber`** | `0.11.4` | Structural PDF text extractor supporting character coordinates, multi-column layouts, and table extraction. |
| **`PyPDF2`** | `3.0.1` | Fallback lightweight PDF parser and page counter. |
| **`python-docx`** | `>=1.1.0` | Native Microsoft Word (`.docx`) file text, table, and paragraph parser. |
| **`openpyxl`** | `>=3.1.0` | Native Microsoft Excel (`.xlsx`) spreadsheet parser. |
| **`python-pptx`** | `>=1.0.0` | Native Microsoft PowerPoint (`.pptx`) slide parser. |
| **`striprtf`** | `>=0.0.26` | Rich Text Format (`.rtf`) plain text converter. |
| **`pandas`** | `>=2.0.0` | Dataframe manipulation library for processing tabular spreadsheet uploads. |
| **`tiktoken`** | `0.7.0` | OpenAI Byte-Pair Encoding (BPE) tokenizer used to split text into accurate token chunks before embedding. |
| **`slowapi`** | `0.1.9` | Rate-limiting library based on Redis / remote IP tracking to protect API endpoints against abuse. |
| **`passlib[bcrypt]`** | `1.7.4` | Password hashing library implementing `bcrypt` for user password security. |
| **`python-jose[cryptography]`** | `3.3.0` | Cryptographic JWT (JSON Web Token) encoding, decoding, and signature verification library. |
| **`python-multipart`** | `0.0.12` | Form-data and HTTP file upload parser for handling binary document uploads. |
| **`httpx`** | `0.27.2` | Async HTTP client for external API requests (Groq API, Gemini API, external webhooks). |
| **`aiofiles`** | `24.1.0` | Asynchronous file I/O utilities for temporary local disk storage during file processing. |

---

## 3. Frontend Dependencies (TypeScript / JavaScript)

All frontend dependencies are defined in `frontend/package.json`:

| Package | Version | Purpose & Usage in DMS |
|---------|---------|------------------------|
| **`next`** | `14.0.0` | React Framework for production providing App Router, Server Side Rendering (SSR), API route proxying, and asset optimization. |
| **`react`** | `^18.0.0` | UI component library powering client interactivity. |
| **`react-dom`** | `^18.0.0` | DOM bindings for React rendering engine. |
| **`typescript`** | `^5.0.0` | Static type system ensuring type safety across component props, API payloads, and state models. |
| **`tailwindcss`** | `^3.3.0` | Utility-first CSS framework used to build custom dark-mode glassmorphic interface components. |
| **`lucide-react`** | `^0.300.0` | Icon set for UI actions (file types, search buttons, folder tree, download links, action feedback). |
| **`mammoth`** | `^1.8.0` | Client-side Word (`.docx`) file renderer converting Word files directly to clean HTML in document preview modals. |
| **`xlsx`** | `^0.18.5` | Client-side spreadsheet renderer rendering Excel files into interactive HTML data tables in preview modals. |
| **`autoprefixer`** | `^10.0.1` | PostCSS plugin parsing CSS and adding vendor prefixes. |
| **`postcss`** | `^8.0.0` | CSS transformation tool processing Tailwind directives into production CSS bundles. |

---

## 4. Infrastructure Services & Container Images

| Container / Tool | Docker Image | Port | Description |
|------------------|--------------|------|-------------|
| **PostgreSQL + pgvector** | `ankane/pgvector:latest` | `5432` | Primary database hosting relational models and HNSW vector similarity search. |
| **Redis** | `redis:7-alpine` | `6379` | In-memory key-value store used as Celery task broker and Layer-0 semantic query cache. |
| **MinIO** | `minio/minio:latest` | `9000` / `9001` | S3-compatible local object storage server with web administration console (Port `9001`). |
| **FastAPI App** | Custom (Python 3.11 Dockerfile) | `8000` | Application API server running Uvicorn. |
| **Celery Worker** | Custom (Python 3.11 Dockerfile) | N/A | Background task processing node. |
| **Flower Dashboard** | Custom (Python 3.11 Dockerfile) | `5555` | Task monitor web UI. |
| **Next.js Web** | Custom (Node.js 18 Dockerfile) | `3000` | Next.js web application frontend. |
