# Product Specifications Document: AI Document Management System

## 1. System Overview
The proposed Document Management System (DMS) is a highly scalable, domain-agnostic, multi-tenant platform. It utilizes Retrieval-Augmented Generation (RAG) to provide an intelligent search interface that allows users to rapidly find, verify, and download specific documents. Rather than memorizing documents, the AI dynamically extracts metadata on upload, indexes vector embeddings, and performs hybrid search (semantic + metadata filtering) to return exact S3 download links and contextual snippets.

## 2. Core Tech Stack
- **Frontend**: Next.js (React), Tailwind CSS
- **Backend**: Python (FastAPI)
- **OCR & Document Parsing**: LlamaParse (LlamaIndex) or Google Cloud Vision API
- **Dynamic Extraction (Ingestion Brain)**: GPT-4o-mini or Claude 3.5 Haiku
- **AI Orchestration Framework**: LlamaIndex
- **Database**: PostgreSQL
- **Database Extensions**: pgvector for embeddings, JSONB for flexible metadata
- **Caching Layer**: Redis
- **Re-ranking Layer**: Cohere Rerank
- **Main Generative LLM**: GPT-4o or Claude 3.5 Sonnet
- **Storage**: AWS S3

## 3. Architecture & Data Flow
### 3.1. Phase 1: Ingestion Pipeline (Upload & Indexing)
1.  **File Upload**: The client uploads a document via the UI. The file is saved directly to a tenant-isolated AWS S3 bucket.
2.  **Multilingual & Handwriting Parsing**: The raw file is routed to LlamaParse or Google Cloud Vision to extract text, tables, and layout metadata (e.g., page numbers, bounding boxes) with high fidelity.
3.  **Dynamic Metadata Extraction**: A fast LLM reads the extracted text in a zero-shot capacity and outputs a JSON object containing dynamically identified metadata (e.g., Document Type, Key Names, Dates, Urgency).
4.  **Vectorization & Storage**: LlamaIndex chunks the text while retaining spatial mapping (page numbers). Chunks are embedded into vectors and stored in PostgreSQL (pgvector). The dynamic JSON object is stored alongside it in a JSONB column.

### 3.2. Phase 2: Retrieval Pipeline (Search & Output)
1.  **Semantic Caching (Layer 0)**: The system checks Redis for identical recent queries. If found, it instantly returns cached results and bypasses the database.
2.  **Hybrid Search (Layer 1)**: The user's natural language query is translated by the LLM into strict JSONB database filters combined with a semantic vector representation. PostgreSQL executes an HNSW (Hierarchical Navigable Small World) index search to retrieve the top 20 candidate chunks.
3.  **Cross-Encoder Re-ranking (Layer 2)**: Cohere Rerank evaluates the 20 chunks against the user's query, dropping irrelevant noise and retaining only the top 3 most relevant chunks.
4.  **Final Generation**: The main LLM synthesizes a brief summary confirming what was found based strictly on the top 3 chunks.
5.  **Payload Delivery**: FastAPI returns a structured JSON payload containing the summary, S3 pre-signed URLs, and page numbers to the frontend.

## 4. Database Schema (PostgreSQL)

| Column Name   | Data Type    | Description                                                                 |
|---------------|--------------|-----------------------------------------------------------------------------|
| `chunk_id`    | `UUID` (PK)  | Unique identifier for the document text chunk.                              |
| `tenant_id`   | `UUID` (FK)  | Identifier for the specific business/client. Used for isolation.            |
| `document_id` | `UUID` (FK)  | Identifier linking to the master document record.                           |
| `content`     | `TEXT`       | The raw text of the document chunk.                                         |
| `embedding`   | `VECTOR(1536)`| The vector representation of the chunk.                                     |
| `metadata`    | `JSONB`      | Dynamically extracted attributes (e.g., `{"type": "complaint", "urgency": "high"}`). |
| `page_number` | `INTEGER`    | The physical page number where the chunk is located.                        |
| `s3_path`     | `VARCHAR`    | The URI for the raw document in AWS S3.                                     |

## 5. API Contracts
### 5.1. Search & Retrieval Endpoint
`POST /api/v1/search`

**Description**: Accepts a user query and returns AI-summarized results alongside direct document access links.

**Request Payload**:
```json
{
  "tenant_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv",
  "query": "Search for citizen complaints regarding pothole repairs filed between January and March.",
  "user_id": "u8v7w6x5-4321-09fe-dcba-zyxwvutsrqpo"
}
```

**Response Payload**:
```json
{
  "ai_summary": "Found 3 matching citizen complaints regarding pothole repairs filed between January and March.",
  "results": [
    {
      "document_name": "Complaint_00452.pdf",
      "download_url": "https://s3.aws.com/tenant-bucket/presigned-link-1",
      "page_number": 2,
      "snippet": "...severe pothole damage reported on Main St...",
      "metadata": {
        "type": "complaint", 
        "urgency": "high"
      }
    },
    {
      "document_name": "Complaint_00891.pdf",
      "download_url": "https://s3.aws.com/tenant-bucket/presigned-link-2",
      "page_number": 1,
      "snippet": "...requesting immediate repair of pothole near the highway exit...",
      "metadata": {
        "type": "complaint", 
        "urgency": "medium"
      }
    }
  ]
}
```

## 6. Security & Multi-Tenancy
-   **Row-Level Security (RLS)**: Implemented natively in PostgreSQL. Every database query automatically validates the `tenant_id` associated with the request token. This guarantees at the database level that queries executed by one tenant cannot retrieve vectors or metadata belonging to another tenant.
-   **S3 Isolation**: AWS S3 buckets are partitioned by `tenant_id`. Access to raw documents is governed strictly via temporary pre-signed URLs generated by the backend on the fly during a successful search.
-   **LLM Data Privacy**: Zero-retention policies must be enforced via the API agreements with the chosen LLM providers to ensure customer documents are never utilized for foundational model training.
