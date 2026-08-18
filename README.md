# Multi-Tenant AI Document Search Platform

A production-ready platform for multi-tenant document ingestion, processing, and vector search with row-level security.

This repo is the **backend** — a FastAPI service plus the Postgres/Redis/MinIO/Celery stack it depends on. The Next.js frontend lives in its own repo: [DMS-frontend](https://github.com/gaurav-chaudhari-sdms-493/DMS-frontend).

## Architecture

```text
       [ User / API ]
             │
             ▼
    [ Next.js Frontend ]  (DMS-frontend repo, Port 3000)
             │
             ▼
    [ FastAPI Backend ]  (Port 8000)
       ┌─────┴──────────┬──────────┐
       │                │          │
       ▼                ▼          ▼
[ Celery Worker ]  [ Redis ]   [ PostgreSQL + pgvector ]
 (Async Tasks)     (Port 6379)         (Port 5432)
```

## Documentation Suite

The system includes comprehensive documentation for technical evaluation, setup, architecture, costing, and live demonstration:

| Document | Description |
|----------|-------------|
| 📐 [**System Architecture & Security**](./docs/SYSTEM_ARCHITECTURE.md) | Component diagrams, multi-tenant Row-Level Security (RLS), and database schemas. |
| 🧠 [**AI Pipeline & Provider Hot-Swapping**](./docs/AI_PIPELINE_AND_MODELS.md) | 4-layer RAG engine, vector chunking, metadata extraction, and provider configuration. |
| 📚 [**Libraries & Tech Stack**](./docs/LIBRARIES_AND_TECH_STACK.md) | Full breakdown of all backend Python packages, frontend React/Next.js libraries, and container dependencies. |
| 🔌 [**Backend REST API Reference**](./docs/BACKEND_ENDPOINTS.md) | Complete REST API specification covering Auth, Ingestion, Search, Chat, Folders, and Tenant Admin. |
| 🛠️ [**Full Setup & Installation Guide**](./docs/SETUP_GUIDE.md) | Step-by-step setup guide for Docker Compose and local native development. |
| 💰 [**Cloud Costing & Estimation**](./docs/COSTING_AND_ESTIMATION.md) | AWS cloud infrastructure hosting costs, AI API token pricing per 1,000 docs/queries, TCO tiers, and ROI strategies. |
| 🎬 [**Demo & Presentation Guide**](./docs/DEMO_PRESENTATION_GUIDE.md) | Step-by-step script and cheat sheet for conducting a live demonstration. |


## Quick Start

1. **Prerequisites**: Docker and Docker Compose installed.
2. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd "Document Search Engine"
   ```
3. **Configure Environment Variables**:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Edit `backend/.env` and fill in the required values (especially passwords, JWT secret, and API keys).
4. **Start the Services**:
   ```bash
   docker compose up --build
   ```
   This brings up the backend stack only (API, Postgres, Redis, MinIO, Celery worker/Flower). Check the container logs to monitor progress.
5. **Run the frontend**: clone [DMS-frontend](https://github.com/gaurav-chaudhari-sdms-493/DMS-frontend) separately and point `NEXT_PUBLIC_API_URL` at this backend (`http://localhost:8000` by default) — see that repo's README for setup.

For more detailed instructions on the Docker setup, see the [Docker README](./docker/README.md).

## Services Reference

| Service   | Description                              | Port |
|-----------|-------------------------------------------|------|
| Backend   | FastAPI Python server                    | 8000 |
| Postgres  | pgvector database                        | 5432 |
| Redis     | Caching & task queue store               | 6379 |
| MinIO     | S3-compatible object storage (+ console) | 9000 / 9001 |
| Worker    | Celery background worker                 | N/A  |
| Flower    | Celery dashboard                         | 5555 |

Frontend (Next.js web app, port 3000) lives in the separate [DMS-frontend](https://github.com/gaurav-chaudhari-sdms-493/DMS-frontend) repo.

## Environment Variables Reference

| Variable Group | Examples / Description |
|----------------|------------------------|
| Database       | `POSTGRES_PASSWORD`, `POSTGRES_URL` |
| Redis          | `REDIS_PASSWORD`, `REDIS_URL` |
| JWT Config     | `JWT_SECRET_KEY`, `JWT_ALGORITHM` |
| AWS S3         | `AWS_ACCESS_KEY_ID`, `S3_BUCKET_NAME` |
| AI Providers   | `AI_LLM_PROVIDER`, `OPENAI_API_KEY`, etc. |
| App Config     | `APP_ENV`, `CORS_ORIGINS`, `RATE_LIMIT_PER_USER` |

*Refer to `backend/.env.example` for the complete list.*

## API Endpoints (Preview)

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| GET    | `/api/v1/health` | No | System health, DB/Redis ping, and RLS verification |
| POST   | `/api/v1/auth/login` | No | Authenticate and get JWT token |
| GET    | `/api/v1/documents` | Yes | List documents for current tenant |
| POST   | `/api/v1/documents` | Yes | Upload and initiate processing |
| POST   | `/api/v1/search/` | Yes | Perform hybrid search with HyDE fallback & query expansion |
| GET    | `/api/v1/admin/tenants` | Yes (Admin) | List tenants |

## Default Credentials

A default tenant and admin user are seeded in the database:
- **Email**: `admin@example.com`
- **Password**: `changeme`

## Swapping AI Providers

The platform supports multiple AI providers for LLMs, embeddings, and OCR. To swap providers, simply update your `.env` file. For instance, to switch from OpenAI to Anthropic for LLM capabilities:

```env
AI_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
```

## Development

To run services locally outside of Docker:
- **Backend**: 
  ```bash
  cd backend
  pip install -r requirements.txt
  alembic upgrade head
  uvicorn main:app --reload --port 8000
  ```
- **Celery Worker**:
  ```bash
  cd backend
  celery -A app.tasks.worker.celery_app worker --loglevel=info
  ```

For frontend development, see [DMS-frontend](https://github.com/gaurav-chaudhari-sdms-493/DMS-frontend).

## Phase 2 Roadmap

- **Celery Workers**: Shift background document processing and embedding to Celery workers for scalability. **(Done)**
- **Row-Level Security (RLS)**: PostgreSQL native tenant isolation across all tables. **(Done)**
- **HyDE & Multilingual Search**: Trilingual HyDE retrieval fallback & multilingual query expansion. **(Done)**
- **Global AI Singleton Caching**: Thread-safe provider factory singleton caching. **(Done)**
- **Compliance Dashboard**: Add UI components to monitor audit logs and ensure SOC2/GDPR compliance.
- **RBAC UI**: Build interfaces to intuitively manage roles and granular resource permissions.