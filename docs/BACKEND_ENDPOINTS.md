# Backend REST API Specification

## 1. OpenAPI & Swagger Information

The FastAPI application auto-generates interactive Swagger and ReDoc documentation.
- **Base URL**: `http://localhost:8000/api/v1`
- **Swagger Interactive UI**: `http://localhost:8000/api/docs`
- **ReDoc UI**: `http://localhost:8000/api/redoc`

---

## 2. Authentication & Authorization Standard

All non-auth endpoints require a standard OAuth2 HTTP Bearer token header:

```http
Authorization: Bearer <access_token>
```

### Access Token Claims (`TokenPayload`)
- `sub`: User ID (`UUID`)
- `tenant_id`: Tenant ID (`UUID`)
- `role`: Role (`admin` | `user` | `viewer`)
- `exp`: Token Expiration Timestamp

---

## 3. API Endpoints Catalog

### 3.1 Auth & User Profile Routes (`/api/v1/auth`)

#### `POST /api/v1/auth/sign-up`
- **Description**: Registers a new company tenant and creates the initial admin user account.
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "admin@acme.com",
  "password": "SecurePassword123!",
  "full_name": "Jane Doe",
  "organization_name": "Acme Corporation"
}
```
- **Response `201 Created`**:
```json
{
  "user_id": "a1b2c3d4-...",
  "tenant_id": "e5f6g7h8-...",
  "email": "admin@acme.com",
  "full_name": "Jane Doe",
  "organization_name": "Acme Corporation"
}
```

#### `POST /api/v1/auth/login`
- **Description**: Authenticates user credentials and issues access & refresh tokens.
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "admin@example.com",
  "password": "changeme"
}
```
- **Response `200 OK`**:
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### `GET /api/v1/auth/me`
- **Description**: Retrieves current authenticated user profile, organization stats, and file type analytics.
- **Auth Required**: Yes
- **Response `200 OK`**:
```json
{
  "user_id": "a1b2c3d4-...",
  "full_name": "Jane Doe",
  "email": "admin@acme.com",
  "role": "admin",
  "tenant_id": "e5f6g7h8-...",
  "tenant_name": "Acme Corporation",
  "created_at": "July 24, 2026",
  "total_files": 42,
  "total_folders": 6,
  "total_size_bytes": 10485760,
  "total_chunks": 350,
  "file_types_breakdown": [
    { "extension": "pdf", "count": 25, "size_bytes": 7340032 },
    { "extension": "docx", "count": 10, "size_bytes": 2097152 }
  ]
}
```

#### `POST /api/v1/auth/refresh`
- **Description**: Exposes token renewal endpoint to issue new access tokens using a valid refresh token.
- **Auth Required**: No (Refresh Token parameter)

#### `POST /api/v1/auth/forgot-password` & `POST /api/v1/auth/reset-password`
- **Description**: Password reset flow endpoints.

---

### 3.2 Document Ingestion & Management (`/api/v1/documents`)

#### `POST /api/v1/documents/`
- **Description**: Uploads a single document file for tenant-isolated storage and queues asynchronous ingestion in Celery.
- **Auth Required**: Yes
- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `file`: Binary file upload (`PDF`, `DOCX`, `XLSX`, `PPTX`, `RTF`, `TXT`)
  - `folder_id` (optional): Target folder `UUID`
- **Response `201 Created`**:
```json
{
  "id": "doc_98765432-...",
  "title": "Q3_Financial_Report.pdf",
  "status": "processing",
  "task_id": "celery-task-uuid-1234",
  "created_at": "2026-07-24T12:00:00Z"
}
```

#### `POST /api/v1/documents/bulk`
- **Description**: Multi-file batch upload endpoint.
- **Auth Required**: Yes
- **Content-Type**: `multipart/form-data` (`files` list)

#### `GET /api/v1/documents`
- **Description**: Lists documents for current tenant with optional folder and status filtering.
- **Auth Required**: Yes
- **Query Parameters**:
  - `folder_id` (`UUID`, optional)
  - `include_all` (`bool`, default: `false`)
  - `is_starred` (`bool`, optional)
  - `is_trashed` (`bool`, default: `false`)
- **Response `200 OK`**: Array of `DocumentListItem`.

#### `GET /api/v1/documents/drive/stats`
- **Description**: Returns storage usage metrics, total documents, and quota stats.

#### `GET /api/v1/documents/{document_id}`
- **Description**: Retrieves full metadata, page numbers, dynamic JSON attributes, and temporary S3 pre-signed URL for a specific document.

#### `PATCH /api/v1/documents/{document_id}`
- **Description**: Renames document or updates metadata.

#### `POST /api/v1/documents/{document_id}/star` & `POST /api/v1/documents/{document_id}/trash`
- **Description**: Toggles star state or moves document to trash bin.

#### `DELETE /api/v1/documents/{document_id}`
- **Description**: Permanently deletes a document record, vector embeddings, and S3 objects.

---

### 3.3 Search & RAG Chat (`/api/v1/search` & `/api/v1/chat`)

#### `POST /api/v1/search/`
- **Description**: Executes 4-layer hybrid search (Redis semantic cache -> PostgreSQL HNSW vector search + JSONB filters -> Cohere cross-encoder rerank -> Generative LLM synthesis).
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "query": "Find citizen complaints regarding pothole repairs on Main Street",
  "limit": 5,
  "filters": {
    "urgency": "high"
  }
}
```
- **Response `200 OK`**:
```json
{
  "ai_summary": "Found 2 citizen complaints regarding urgent pothole repairs on Main Street.",
  "cached": false,
  "results": [
    {
      "document_id": "doc_12345678-...",
      "document_name": "Complaint_Main_St.pdf",
      "download_url": "http://localhost:9000/docsearch-documents/tenant_id/doc_id/file.pdf?X-Amz-Signature=...",
      "page_number": 2,
      "snippet": "...severe pothole damage reported on Main St causing traffic delay...",
      "rerank_score": 0.942,
      "metadata": {
        "document_type": "complaint",
        "urgency": "high"
      }
    }
  ]
}
```

#### `POST /api/v1/chat/`
- **Description**: Interactive RAG conversation endpoint accepting message history and returning cited document responses.

---

### 3.4 Folder Hierarchy Management (`/api/v1/folders`)

- `GET /api/v1/folders`: Returns tenant folder tree hierarchy.
- `POST /api/v1/folders`: Creates a new directory folder.
- `DELETE /api/v1/folders/{folder_id}`: Removes folder.

---

### 3.5 Tenant Administration & Audit Logs (`/api/v1/admin`)

- `GET /api/v1/admin/tenants`: Lists all tenant organizations (Admin only).
- `POST /api/v1/admin/tenants`: Creates new organization tenant (Admin only).
- `GET /api/v1/admin/audit-logs`: Retrieves security access logs and IP activity history.
- `GET /api/v1/admin/system-stats`: Returns system telemetry, vector count, and Celery task performance metrics.
