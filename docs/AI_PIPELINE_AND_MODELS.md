# AI Pipeline, Models & Provider Configuration

## 1. AI System Overview

The DMS AI engine combines multi-format document extraction, dynamic schema-less metadata extraction, high-dimensional vector embeddings, hybrid PostgreSQL HNSW search, cross-encoder re-ranking, and generative RAG synthesis into a multi-layer pipeline.

All AI integrations are modularized using provider adapters, allowing seamless hot-swapping between OpenAI, Anthropic, Groq, Cohere, and Google Gemini via `.env` configuration without code changes.

### 1.1 Global AI Provider Singleton Caching
To eliminate model initialization overhead, API client instantiation latency, and memory bloat, provider instances (`LLMProvider`, `EmbeddingProvider`) are cached thread-safely via a global provider singleton factory (`get_ai_provider_factory()`). Provider instances are instantiated once per configuration key and reused across all concurrent requests.

---

## 2. Ingestion Pipeline (Upload & Indexing)

```
[ Raw File ] ──► [ Text & Table Extractor ] ──► [ Ingestion Brain LLM ] ──► [ Text Chunker ] ──► [ Embedding Generator ] ──► [ PostgreSQL ]
(PDF, DOCX,      (pdfplumber / LlamaParse /       (Extracts JSON metadata:    (500 tokens,         (1024-dim BGE-M3 vectors) (pgvector HNSW +
 XLSX, PPTX)     python-docx / openpyxl)          category, urgency, dates)   50 token overlap)                            JSONB Metadata)
```

### 2.1 Multi-Format Document Parsing
- **PDF Documents**: Parsed with `pdfplumber` and `PyPDF2` for structural text extraction and page-by-page table extraction.
- **Word Documents (`.docx`)**: Parsed using `python-docx` for paragraph structures, tables, and header formatting.
- **Spreadsheets (`.xlsx`, `.xls`)**: Parsed with `openpyxl` and `pandas` into tabular representations.
- **Presentations (`.pptx`)**: Parsed using `python-pptx` to extract slide text and notes.
- **Rich Text / Text (`.rtf`, `.txt`, `.csv`)**: Processed using `striprtf` and native UTF-8 streaming.
- **Complex Scanned PDFs / OCR**: Supports `LlamaParse` integration for layout-aware optical character recognition.

### 2.2 Ingestion Brain (Dynamic Metadata Extraction)
When a document is parsed, the raw text is sent to a fast LLM (e.g., `gpt-4o-mini`, `claude-3-5-haiku`, or `llama-3.3-70b-versatile` via Groq) to dynamically infer document metadata without pre-defined fixed schemas.

**Extracted Attributes**:
- `document_type`: (e.g., invoice, contract, citizen complaint, technical report, meeting minutes)
- `category` & `tags`: Domain keywords automatically categorized.
- `urgency`: (e.g., low, medium, high, critical)
- `key_entities`: Names of companies, individuals, products, or locations mentioned.
- `effective_dates` / `timestamps`: Extracted calendar dates.

**Database Storage**: Stored as PostgreSQL native `JSONB` on both the document master record and individual chunk records, enabling fast indexed metadata filtering alongside vector similarity search.

### 2.3 Semantic Text Chunking
- **Chunk Size**: 500 tokens per chunk.
- **Overlap**: 50 tokens overlap between contiguous chunks to preserve edge context across boundaries.
- **Page Association**: Every chunk retains its exact origin `page_number`, enabling precise page-level citations in RAG answers.

---

## 3. Retrieval Pipeline (Search & RAG Synthesis)

The platform employs a **4-Layer Retrieval Pipeline** to maximize precision and minimize LLM token cost.

```
[ User Query ]
      │
      ▼
Layer 0: Redis Semantic Caching ──────(Cache Hit)──────► Return Instant Result
      │
      │ (Cache Miss)
      ▼
Layer 1: PostgreSQL Hybrid Search (pgvector HNSW Cosine Similarity + JSONB Filter) ──► Top 20 Candidates
      │
      ▼
Layer 2: Cohere Cross-Encoder Re-Ranking (rerank-english-v3.0) ─────────────────────────► Top 3 Relevant Chunks
      │
      ▼
Layer 3: Generative LLM RAG Synthesis (GPT-4o / Claude 3.5 Sonnet) ──────────────────────► Final Summary & Citations
```

### Layer 0: Redis Semantic Caching
- **Mechanism**: Hashes incoming query strings + tenant ID into Redis cache keys with 1-hour TTL.
- **Benefit**: Bypasses vector DB search and LLM synthesis entirely for frequent or identical queries, reducing response time to `< 10ms` and lowering API costs by 35-50%.

### Layer 1: Hybrid Search (HNSW Vector + Full-Text Search + Metadata Filtering)
- **Vector Search**: Computes cosine distance between query embedding and stored chunk embeddings using PostgreSQL `pgvector` with HNSW indexes (`m=16`, `ef_construction=64`).
- **HyDE (Hypothetical Document Embeddings) Fallback**: When `hyde_enabled=true` (or when standard search yields low relevance), an LLM generates a synthetic answer/hypothetical passage in the target language (English, Spanish, or French). The synthetic passage is embedded to perform dense semantic retrieval, significantly improving recall for abstract or short queries.
- **Multilingual Query Expansion**: Parses and expands input queries across supported languages (English, Spanish, French, German, Japanese, Chinese, Hindi) into expanded synonym/translation sets.
- **Full-Text Search (`websearch_to_tsquery`)**: Converts user queries into PostgreSQL `tsquery` objects with full operator support (`AND`, `OR`, `"phrase quotes"`, `-exclusion`).
- **Metadata Filtering**: Dynamically parses natural language queries into JSONB SQL expressions (e.g., `metadata->>'urgency' = 'high' AND metadata->>'document_type' = 'complaint'`).
- **Candidate Pool**: Merges vector and full-text candidates using Reciprocal Rank Fusion (RRF) to select the top 20 candidate chunks.

### Layer 2: Cross-Encoder Re-Ranking (Cohere Rerank)
- **Model**: `rerank-english-v3.0` (or `rerank-multilingual-v3.0`).
- **Purpose**: Evaluates candidate chunks against query intent to filter out false-positive vector matches.
- **Output**: Trims top 20 candidate chunks down to the top 3 highest-quality chunks.

### Layer 3: Generative RAG Synthesis
- **Model**: Main generative LLM (`gpt-4o`, `claude-3-5-sonnet`, or `llama-3.3-70b-versatile`).
- **Prompt Guardrails**: Strictly instructs the LLM to summarize findings using *only* the top 3 provided context chunks. If the document content does not contain sufficient answer detail, the model explicitly declares inability to verify rather than hallucinating.
- **Citation Metadata**: Returns document title, S3 pre-signed URL, exact page number, text snippet, and dynamic tags.

---

## 4. Supported AI Models & Providers

| Role | Default Model | Supported Providers / Fallbacks |
|------|---------------|----------------------------------|
| **Ingestion Brain** | `gpt-4o-mini` | Anthropic (`claude-3-5-haiku`), Groq (`llama-3.3-70b-versatile`) |
| **Embeddings** | `BAAI/bge-m3` (1024d) | OpenAI (`text-embedding-3-small`), Google Gemini (`text-embedding-004`), Cohere |
| **Re-Ranking** | `rerank-english-v3.0` | Cohere Rerank API, Local Cross-Encoder |
| **Generative RAG** | `gpt-4o` | Anthropic (`claude-3-5-sonnet`), Groq (`llama-3.3-70b-versatile`) |
| **Document OCR** | `pdfplumber` (native) | LlamaParse (LlamaIndex Cloud API) |

---

## 5. Hot-Swapping Provider Configuration Guide

To switch AI providers, update the key-value parameters in `backend/.env`. No code edits or server rebuilds are required.

### Example 1: Switch LLM from OpenAI to Anthropic
```env
AI_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_LLM_MODEL=claude-3-5-haiku-20241022
```

### Example 2: Switch LLM to Groq (Llama 3.3 70B) with Key Rotation
```env
AI_LLM_PROVIDER=groq
GROQ_API_KEY=gsk_key1...
GROQ_API_KEY1=gsk_key2...
GROQ_LLM_MODEL=llama-3.3-70b-versatile
```

### Example 3: Switch Embeddings to Google Gemini
```env
AI_EMBED_PROVIDER=gemini
GOOGLE_API_KEY=AIzaSy...
GEMINI_EMBED_MODEL=text-embedding-004
```

### Example 4: Enable LlamaParse OCR for Complex Scanned PDFs
```env
AI_OCR_PROVIDER=llamaparse
LLAMAPARSE_API_KEY=llx-...
```
