# Cloud Infrastructure & AI API Costing Model

This document outlines the operational cloud infrastructure and AI API token costing for deploying and scaling the Multi-Tenant AI Document Management & Search Platform.

---

## 1. Cloud Infrastructure Costing (AWS Hosting Estimates)

Infrastructure costs are divided into Compute (FastAPI & Celery Workers), Database (PostgreSQL + pgvector), Cache (Redis), and Storage (S3).

| Resource Layer | Recommended AWS Provisioning | Monthly Cost (Est.) |
|----------------|------------------------------|---------------------|
| **API & Worker Compute** | AWS ECS Fargate / 2x `t4g.medium` (2 vCPU, 4GB RAM) | $35 - $60 / mo |
| **PostgreSQL Database** | AWS RDS PostgreSQL `db.t4g.medium` (2 vCPU, 4GB RAM, 50GB gp3 storage with `pgvector`) | $50 - $90 / mo |
| **Redis Cache & Queue** | AWS ElastiCache for Redis `cache.t4g.micro` (0.5GB RAM) | $15 - $25 / mo |
| **Object Storage** | AWS S3 Standard Storage (~100 GB files) + Data Transfer | $5 - $15 / mo |
| **Total Base Infrastructure** | **Small Enterprise Production Environment** | **~$105 - $190 / month** |

*Note: For early development or single-node VPS hosting (e.g., DigitalOcean / Hetzner), total base infrastructure can be hosted on a single $24 - $40/mo VM.*

---

## 2. AI Operational API Pricing Breakdown

Costs for AI operations depend directly on document volume and search query frequency.

### 2.1 Ingestion Cost per 1,000 Documents
*Assumptions per document*: Average 5 pages, ~2,500 total words (~3,300 tokens), yielding ~7 text chunks (500 tokens per chunk).

| Ingestion Step | Provider & Model | Unit Cost | Cost per 1,000 Docs |
|----------------|------------------|-----------|----------------------|
| **Dynamic Metadata Extraction** | OpenAI `gpt-4o-mini` | $0.150 / 1M input tokens<br>$0.600 / 1M output tokens | ~$0.55 |
| **Vector Embeddings (7 chunks/doc)** | OpenAI `text-embedding-3-small` | $0.020 / 1M tokens | ~$0.05 |
| **Alternative: Ingestion LLM via Groq** | Groq `llama-3.3-70b-versatile` | $0.590 / 1M input tokens | ~$1.95 |
| **Total Ingestion Cost (Default Stack)** | **`gpt-4o-mini` + `text-embedding-3-small`** | **—** | **~$0.60 / 1,000 documents** |

---

### 2.2 Retrieval & Search Cost per 1,000 Search Queries
*Assumptions per query*: 50 tokens query length, 20 candidate chunks evaluated, top 3 chunks (1,500 tokens context) passed to RAG synthesis (300 tokens generated output).

| Search Layer | Provider & Model | Unit Cost | Cost per 1,000 Queries |
|--------------|------------------|-----------|------------------------|
| **Layer 0: Redis Semantic Cache** | In-Memory Redis | $0.00 (Local compute) | $0.00 (35-50% queries hit cache) |
| **Query Embedding Generation** | OpenAI `text-embedding-3-small` | $0.020 / 1M tokens | ~$0.001 |
| **Layer 2: Cross-Encoder Re-Ranking** | Cohere Rerank (`rerank-v3.0`) | $2.00 / 1,000 search units | ~$2.00 |
| **Layer 3: Generative RAG Answer Synthesis** | OpenAI `gpt-4o` (or `gpt-4o-mini`) | `gpt-4o-mini`: $0.15 / 1M in<br>`gpt-4o`: $2.50 / 1M in | `gpt-4o-mini`: ~$0.40<br>`gpt-4o`: ~$4.50 |
| **Total Search Cost (With Rerank + `gpt-4o-mini`)** | **Default Stack** | **—** | **~$2.40 / 1,000 search queries** |

---

## 3. Total Cost of Ownership (TCO) Scenarios

```
       ┌─────────────────────────────────────────────────────────────┐
       │                   MONTHLY TCO COMPARISON                    │
       ├───────────────────┬───────────────────┬─────────────────────┤
       │   Startup Tier    │   Growth Tier     │   Scale Enterprise  │
       │   10k Documents   │   100k Documents  │   1M Documents      │
       │   5k Queries/mo   │   50k Queries/mo  │   500k Queries/mo   │
       ├───────────────────┼───────────────────┼─────────────────────┤
       │   ~$45 - $80/mo   │  ~$250 - $450/mo  │ ~$1,200 - $2,100/mo │
       └───────────────────┴───────────────────┴─────────────────────┘
```

### Tier 1: Startup / Small Business
- **Storage / Ingestion Volume**: 10,000 documents uploaded per month.
- **Search Activity**: 5,000 search queries per month.
- **Infrastructure**: Single VPS or minimal AWS Fargate + RDS instance ($35/mo).
- **AI API Charges**:
  - Ingestion: 10 * $0.60 = $6.00
  - Search: 5 * $2.40 = $12.00
- **Total Estimated Cost**: **~$53.00 / month**

### Tier 2: Growth Enterprise
- **Storage / Ingestion Volume**: 100,000 total stored documents.
- **Search Activity**: 50,000 search queries per month.
- **Infrastructure**: Managed AWS Fargate + AWS RDS PostgreSQL + ElastiCache ($175/mo).
- **AI API Charges**:
  - Ingestion (10k new docs/mo): $6.00
  - Search (50k queries/mo, 40% cached = 30k API calls): 30 * $2.40 = $72.00
- **Total Estimated Cost**: **~$253.00 / month**

### Tier 3: High-Scale Enterprise
- **Storage / Ingestion Volume**: 1,000,000 stored documents.
- **Search Activity**: 500,000 search queries per month.
- **Infrastructure**: High-availability multi-node ECS + Multi-AZ RDS PostgreSQL ($650/mo).
- **AI API Charges**:
  - Ingestion (50k new docs/mo): $30.00
  - Search (500k queries/mo, 40% cached = 300k API calls): 300 * $2.40 = $720.00
- **Total Estimated Cost**: **~$1,400.00 / month**

---

## 4. Architectural Cost Optimization Strategies

The system includes built-in architecture mechanisms to reduce operational expenses:

### 1. Redis Layer-0 Semantic Query Caching
- Common queries, repeat searches, or user re-clicks hit the Redis cache instantly without invoking Cohere Rerank or OpenAI APIs.
- **Cost Impact**: Reduces search API charges by **35% to 50%**.

### 2. Candidate Filtering via PostgreSQL HNSW & JSONB
- Instead of feeding hundreds of document chunks to an expensive LLM context window, PostgreSQL `pgvector` HNSW indexes and metadata JSONB filters isolate the top 20 relevant candidates in database memory.
- **Cost Impact**: Saves up to **90% in LLM prompt token consumption**.

### 3. Cohere Cross-Encoder Filtering (Top 20 -> Top 3)
- The re-ranker evaluates 20 candidates and strips out 17 irrelevant chunks before passing context to the main generative LLM.
- **Cost Impact**: Reduces generative LLM prompt context length from ~10,000 tokens down to ~1,500 tokens.

### 4. Hot-Swappable Open Models (Groq / Ollama / Local Embeddings)
- Organizations with strict budgets can hot-swap OpenAI with Groq (`llama-3.3-70b-versatile`) or locally hosted open embeddings (BGE-M3), eliminating external per-token API charges entirely.
