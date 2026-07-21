# Multi-Tenant AI Document Search Platform

A production-ready platform for multi-tenant document ingestion, processing, and vector search with row-level security.

## Architecture

```text
       [ User / API ]
             │
             ▼
    [ Next.js Frontend ] (Port 3000)
             │
             ▼
    [ FastAPI Backend ]  (Port 8000)
       ┌─────┴──────────┬──────────┐
       │                │          │
       ▼                ▼          ▼
[ Celery Worker ]  [ Redis ]   [ PostgreSQL + pgvector ]
 (Async Tasks)     (Port 6379)         (Port 5432)
```

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
   The system will be available after a few moments. Check the container logs to monitor progress.

For more detailed instructions on the Docker setup, see the [Docker README](./docker/README.md).

## Services Reference

| Service   | Description                | Port |
|-----------|----------------------------|------|
| Frontend  | Next.js web application    | 3000 |
| Backend   | FastAPI Python server      | 8000 |
| Postgres  | pgvector database          | 5432 |
| Redis     | Caching & task queue store | 6379 |
| Worker    | Celery background worker   | N/A  |

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
| POST   | `/api/auth/login` | No | Authenticate and get JWT token |
| GET    | `/api/documents` | Yes | List documents for current tenant |
| POST   | `/api/documents` | Yes | Upload and initiate processing |
| GET    | `/api/search` | Yes | Perform hybrid vector search |
| GET    | `/api/admin/tenants` | Yes (Admin) | List tenants |

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
- **Frontend**:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```

## Phase 2 Roadmap

- **Celery Workers**: Shift background document processing and embedding to Celery workers for scalability. **(Done)**
- **Compliance Dashboard**: Add UI components to monitor audit logs and ensure SOC2/GDPR compliance.
- **RBAC UI**: Build interfaces to intuitively manage roles and granular resource permissions.