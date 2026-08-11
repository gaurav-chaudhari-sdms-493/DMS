# DMS — Developer Action Plan

**Project:** Multi-Tenant AI Document Management & Search Platform **Audience:** Junior developer taking ownership of remediation **Version:** 1.0 · 10 August 2026 **Based on:** static audit of `main` @ commit after the `feacture/gdrive-clone` merge

---

## 0\. Read this first

### 0.1 What state the project is actually in

The project has a good architecture and a lot of real, working code — hybrid vector \+ keyword search with Reciprocal Rank Fusion, a Google-Drive-style UI, folders, persistent chat, admin analytics, MinIO object storage, and a pluggable AI provider layer. None of that needs to be thrown away.

**But right now the backend cannot start.** Three files still contain unresolved Git merge conflict markers, one file has 27 undefined variable names, and the database migration chain fails on its very first migration. Nothing you see in the UI screenshots is currently reachable from a clean checkout.

Your job, in order, is: make it start → make it index documents → make the database schema coherent → close the security holes → stop the AI layer from silently fabricating data → improve search quality → then, and only then, look at the desktop app.

### 0.2 Ground rules

1. **Work one phase at a time, in order.** Phases 1–3 are strictly sequential — Phase 2 cannot be tested until Phase 1 is done, and so on. Within a phase, tasks can often be done in parallel.  
2. **One branch and one pull request per phase.** Name them `fix/phase-1-boot`, `fix/phase-2-ingestion`, etc. Do not mix phases in one PR.  
3. **Never commit merge conflict markers.** Before every single commit, run the check in §0.4. This is exactly how the current mess happened.  
4. **Every task has a "Verify" step. Actually run it.** If you cannot run the verification, the task is not done.  
5. **If a fix takes more than 2 hours or the instructions don't match what you see in the file, stop and ask.** The codebase may have moved since this document was written. Do not guess and do not "work around" it — a wrong guess here costs more than a question.  
6. **Do not delete code you don't understand.** Comment it out with a `# TODO(yourname):` note and raise it in standup.

### 0.3 One-time setup

git clone \<repo-url\> && cd DMS

cp backend/.env.example backend/.env

\# Generate a real JWT secret and put it in backend/.env

openssl rand \-hex 32

\# → paste into JWT\_SECRET\_KEY=

\# Python tooling you will need for the verification steps

pip install pyflakes

You do **not** need working API keys for Groq/OpenAI/Cohere to complete Phases 1–4. Leave them blank; the code has fallbacks (which is itself a bug you will fix in Phase 5).

### 0.4 The pre-commit check — run this every time

\# 1\. No merge conflict markers anywhere

grep \-rn "^\<\<\<\<\<\<\< \\|^\>\>\>\>\>\>\> \\|^=======$" \--exclude-dir=.git . && echo "CONFLICT MARKERS FOUND — DO NOT COMMIT" || echo "OK: clean"

\# 2\. All Python compiles

cd backend && find app \-name "\*.py" \-exec python \-m py\_compile {} \\; && echo "OK: python compiles"

\# 3\. No undefined names

python \-m pyflakes app/ | grep "undefined name" && echo "UNDEFINED NAMES — DO NOT COMMIT" || echo "OK: no undefined names"

\# 4\. Frontend type-checks

cd ../frontend && npx tsc \--noEmit && echo "OK: typescript"

Consider wiring these four commands into a Git pre-commit hook on day one. It takes ten minutes and would have prevented every Phase 1 bug.

### 0.5 Glossary

| Term | What it means here |
| :---- | :---- |
| **Tenant** | One customer organisation. All data is meant to be isolated per tenant. |
| **RLS** | PostgreSQL Row-Level Security — the database itself refuses to return rows from other tenants. Currently written but never applied. |
| **Chunk** | A \~512-token slice of a document, stored with a 1024-dimension vector for semantic search. |
| **Embedding** | A list of 1024 numbers representing the meaning of a chunk. Similar meaning → similar numbers. |
| **RRF** | Reciprocal Rank Fusion — the maths that merges vector-search results with keyword-search results into one ranked list. |
| **Reranker** | A second, more accurate model that re-scores the top \~20 candidates and keeps the best few. |
| **Celery** | Background job queue. Document processing is meant to run here so uploads return instantly. |
| **Alembic** | The database migration tool. Each migration is a versioned Python file describing a schema change. |

---

## Phase 1 — Make it compile and boot

**Goal:** `docker compose up --build` brings the backend up and `http://localhost:8000/api/docs` loads. **Estimated effort:** 1 day **Branch:** `fix/phase-1-boot`

### [x] 1.1 Resolve the merge conflict in `auth_service.py`

**File:** `backend/app/services/auth_service.py` **Problem:** Lines 26, 64 and 65 contain `<<<<<<< HEAD`, `=======` and `>>>>>>> main`. Python cannot parse the file, so *every* import of the app fails.

The conflicted block is the `sign_up()` function. `backend/app/api/v1/auth.py` imports `sign_up`, so **you must keep it**.

**Fix:** Delete exactly three lines — line 26 (`<<<<<<< HEAD`), line 64 (`=======`) and line 65 (`>>>>>>> main`). Keep everything between them. The result should read:

def verify\_password(plain: str, hashed: str) \-\> bool:

    ...

async def sign\_up(body: SignUpRequest, db: AsyncSession) \-\> SignUpResponse:

    """Creates a new tenant and an admin user."""

    ...

def create\_access\_token(user\_id: uuid.UUID, tenant\_id: uuid.UUID, role: str) \-\> str:

    ...

**Verify:**

cd backend && python \-m py\_compile app/services/auth\_service.py && echo OK

**Done when:** the file compiles and `grep -c "<<<<<<<" app/services/auth_service.py` returns `0`.

---

### [x] 1.2 Resolve the merge conflict in `pdfplumber_provider.py`

**File:** `backend/app/ocr/providers/pdfplumber_provider.py` **Problem:** Two conflicted blocks — lines 4/6/9 (the imports) and lines 23/26/66 (the body of `extract_pages`).

**Which side wins: HEAD.** This is not a coin toss, and here is why you can be confident:

- The `HEAD` side delegates to `app/ocr/extractor.py`, which handles PDF, DOCX, XLSX, PPTX, CSV, RTF, JSON, images and plain text — matching the file types the Drive UI advertises. It also has a real Tesseract OCR fallback for scanned pages.  
- The `main` side only handles PDFs, and its code calls `pdfplumber.open(...)` and `io.BytesIO(...)` — **neither `pdfplumber` nor `io` is imported anywhere in that file.** That side would crash with `NameError` the first time it ran. It is dead code.

**Fix:** Delete the `main` side entirely. The whole file becomes:

import asyncio

from typing import List

from app.ai.base import OCRProvider

from app.ocr.extractor import extract\_pages\_from\_file

class PdfPlumberProvider(OCRProvider):

    """Multi-format document text extractor.

    Delegates to app.ocr.extractor, which handles PDF, DOCX, XLSX, PPTX,

    CSV, RTF, JSON, images (via Tesseract OCR) and plain text.

    """

    def \_\_init\_\_(self, min\_text\_threshold: int \= 10):

        self.min\_text\_threshold \= min\_text\_threshold

    async def extract\_pages(self, file\_bytes: bytes, filename: str) \-\> List\[dict\]:

        return await asyncio.to\_thread(extract\_pages\_from\_file, file\_bytes, filename)

> **Note for later (Phase 5):** `extractor.py` does not raise `OCRFallbackRequired`; when it cannot read a page it inserts placeholder text like `"Scanned page 1 of document X"`, which then gets embedded and indexed as if it were real content. Task 5.3 deals with this. Leave it alone for now.

**Verify:**

cd backend && python \-m py\_compile app/ocr/providers/pdfplumber\_provider.py && echo OK

---

### [x] 1.3 Resolve the merge conflict in `api.ts`

**File:** `frontend/lib/api.ts` **Problem:** Line 4 is a stray `<<<<<<< HEAD` with **no matching `=======` or `>>>>>>>`** anywhere in the file. Somebody resolved the conflict but forgot the opening marker. TypeScript cannot parse it.

**Fix:** Delete line 4\. That is the entire fix. Everything else in the file is correct.

**Verify:**

cd frontend && npx tsc \--noEmit && echo OK

---

### [x] 1.4 Rewrite `ingestion.py` as a Celery enqueue wrapper

**File:** `backend/app/pipeline/ingestion.py` **Problem:** This file has **27 undefined names**, starting with `logging` on line 6 (`logger = logging.getLogger(__name__)` with no `import logging`). That is a module-level `NameError`. `document_service.py` imports `ingest_document` from this file, so this single bug takes down the entire application at import time.

The file also contains a duplicate, half-finished copy of the ingestion pipeline that references a database session variable `db` which is never created. The real, working pipeline already lives in `backend/app/tasks/worker.py`.

**Fix:** Replace the *entire contents* of `backend/app/pipeline/ingestion.py` with this:

"""Ingestion entry point.

The actual pipeline (OCR → chunk → embed → store) lives in

app/tasks/worker.py and runs inside a Celery worker. This module only

enqueues the job so that the HTTP upload request returns immediately.

"""

import logging

from uuid import UUID

from ..tasks.worker import ingest\_document\_task

logger \= logging.getLogger(\_\_name\_\_)

async def ingest\_document(

    document\_id: UUID,

    version\_id: UUID,

    s3\_path: str,

    tenant\_id: UUID,

) \-\> None:

    """Queue a document for background ingestion."""

    ingest\_document\_task.delay(

        document\_id\_str=str(document\_id),

        version\_id\_str=str(version\_id),

        s3\_path=s3\_path,

        tenant\_id\_str=str(tenant\_id),

    )

    logger.info("Queued document %s (version %s) for ingestion", document\_id, version\_id)

That is the whole file. Do not keep anything else.

**Verify:**

cd backend && python \-m pyflakes app/pipeline/ingestion.py

\# Must print nothing at all.

**Done when:** pyflakes is silent and `grep -rn "\.delay(" app/` shows a call in `ingestion.py` as well as in `reindex_failed.py`.

---

### [x] 1.5 Fix the CORS override

**File:** `backend/app/main.py` **Problem:** The middleware hardcodes `allow_origins=["*"]` together with `allow_credentials=True`. Browsers reject that combination, and it silently ignores the `CORS_ORIGINS` setting that exists in config and `.env.example`.

**Fix:** In `create_app()`, change:

app.add\_middleware(

    CORSMiddleware,

    allow\_origins=\["\*"\],          \# ← replace this line

    allow\_credentials=True,

    ...

)

to:

app.add\_middleware(

    CORSMiddleware,

    allow\_origins=settings.cors\_origins,

    allow\_credentials=True,

    allow\_methods=\["\*"\],

    allow\_headers=\["\*"\],

)

Then set `CORS_ORIGINS=["http://localhost:3000"]` in your `backend/.env`.

**Verify:** After Phase 3, log in from the frontend at `localhost:3000` and confirm no CORS errors in the browser console.

---

### Phase 1 exit criteria

Run all four checks in §0.4. Every one must pass. Do not open the PR until they do.

> The backend container will still fail to *stay* up after this phase, because `alembic upgrade head` is broken. That is expected and is Phase 3's job. What you are proving here is that all the Python and TypeScript is syntactically valid and every module imports.

---

## Phase 2 — Make ingestion actually run

**Goal:** Upload a PDF, and 30 seconds later its status is `indexed` and its text is searchable. **Estimated effort:** 1 day **Depends on:** Phase 1 **Branch:** `fix/phase-2-ingestion`

> You will not be able to fully test this phase until Phase 3 gives you a working database. Do Phase 3 first if you get blocked — the two are tightly coupled, and it is fine to ship them as one PR if that is easier.

### [x] 2.1 Add `tenant_id` to the Chunk model

**File:** `backend/app/models/chunk.py` **Problem:** `worker.py` line 129 constructs `DBChunk(..., tenant_id=tenant_id, ...)` but the `Chunk` model has no `tenant_id` column. SQLAlchemy raises `TypeError: 'tenant_id' is an invalid keyword argument for Chunk` on **every single document ingest**.

You could delete the argument from the worker instead — do not. Keep the column: it lets the search query filter by tenant without joining through `documents`, and Phase 4's RLS policy needs it.

**Fix:** Add the column to the `Chunk` class, just after `document_id`:

class Chunk(Base):

    \_\_tablename\_\_ \= "chunks"

    id: Mapped\[uuid.UUID\] \= mapped\_column(UUID(as\_uuid=True), primary\_key=True, default=uuid.uuid4)

    document\_id: Mapped\[uuid.UUID\] \= mapped\_column(ForeignKey("documents.id"), index=True)

    tenant\_id: Mapped\[uuid.UUID\] \= mapped\_column(ForeignKey("tenants.id"), index=True)   \# ← ADD THIS

    version\_id: Mapped\[Optional\[uuid.UUID\]\] \= mapped\_column(...)

    ...

**Verify:**

cd backend && python \-c "from app.models.chunk import Chunk; print(Chunk.\_\_table\_\_.columns.keys())"

\# 'tenant\_id' must appear in the list.

---

### [x] 2.2 Fix the two `Chunk.chunk_id` references

**Files:** `backend/app/api/v1/auth.py` line 65, `backend/app/api/v1/admin.py` line 57 **Problem:** Both call `select(func.count(Chunk.chunk_id))`. The model's primary key is named `id`, not `chunk_id`. Both endpoints raise `AttributeError` and return HTTP 500\.

The name `chunk_id` comes from the old initial Alembic migration, which disagrees with the model. Phase 3 settles that argument in favour of `id`.

**Fix:** In both files, change `Chunk.chunk_id` to `Chunk.id`.

**Verify:**

cd backend && grep \-rn "Chunk.chunk\_id" app/

\# Must return nothing.

---

### [x] 2.3 Add `full_name` to the User model

**File:** `backend/app/models/user.py` **Problem:** Four places use `User.full_name` — `sign_up()`, the `/auth/me` endpoint, `/admin/analytics`, and `init_db.py` — but the column does not exist. Sign-up raises `TypeError`; the other three raise `AttributeError`.

**Fix:** Add the column:

class User(Base):

    \_\_tablename\_\_ \= "users"

    id: Mapped\[uuid.UUID\] \= mapped\_column(UUID(as\_uuid=True), primary\_key=True, default=uuid.uuid4)

    tenant\_id: Mapped\[uuid.UUID\] \= mapped\_column(ForeignKey("tenants.id"), index=True)

    email: Mapped\[str\] \= mapped\_column(index=True)

    full\_name: Mapped\[str\] \= mapped\_column(default="")          \# ← ADD THIS

    hashed\_password: Mapped\[str\] \= mapped\_column("password\_hash")

    ...

---

### [x] 2.4 Remove the unique constraint on `Tenant.name`

**File:** `backend/app/models/tenant.py` **Problem:** `name` is declared `unique=True`, and `sign_up()` derives the tenant name from the user's full name: `f"{body.full_name}'s Organization"`. The second person called "John Smith" who signs up gets an opaque 500 error.

**Fix:** Change `name: Mapped[str] = mapped_column(unique=True, index=True)` to `name: Mapped[str] = mapped_column(index=True)`.

---

### [x] 2.5 Add a unique constraint on user email

**File:** `backend/app/models/user.py` **Problem:** Nothing at the database level prevents two users registering the same email. `sign_up()` checks in Python first, but two simultaneous requests can both pass that check (a classic race condition) and both insert.

**Fix:** Add a table-level constraint to the `User` class:

from sqlalchemy import UniqueConstraint

class User(Base):

    \_\_tablename\_\_ \= "users"

    \_\_table\_args\_\_ \= (UniqueConstraint("email", name="uq\_users\_email"),)

    ...

---

### [x] 2.6 Cache the AI provider objects

**File:** `backend/app/ai/factory.py` **Problem:** `get_llm_provider()` and `get_embed_provider()` used to cache their result in a module-level variable. That caching was removed. Now a brand-new provider object is built on **every call** — and for the default `bgem3` provider that means the BGE-M3 model (roughly 2 GB) is reloaded from disk on every search and every batch of chunks. Searches that should take 200 ms will take 30+ seconds.

**Fix:** Restore the caching. The module already declares the globals at the top (`_llm_provider`, `_embed_provider`, `_rerank_provider`) — they are just unused. Wrap each factory:

def get\_embed\_provider() \-\> EmbeddingProvider:

    global \_embed\_provider

    if \_embed\_provider is not None:

        return \_embed\_provider

    \# ... existing body that builds primary\_provider and fallback\_provider ...

    if fallback\_provider:

        \_embed\_provider \= FallbackEmbeddingProvider(primary\_provider, fallback\_provider)

    else:

        \_embed\_provider \= primary\_provider

    return \_embed\_provider

Do the same for `get_llm_provider()` and `get_rerank_provider()`.

While you are in this file, delete the duplicated `import logging` and the duplicated `logger = logging.getLogger(__name__)` at lines 1–10 — there are two of each.

**Verify:**

cd backend && python \-c "

from app.ai.factory import get\_embed\_provider

a, b \= get\_embed\_provider(), get\_embed\_provider()

assert a is b, 'provider is not cached'

print('OK: cached')

"

---

### [x] 2.7 Persist the BGE-M3 model between container restarts

**File:** `docker-compose.yml` **Problem:** The BGE-M3 model downloads to `~/.cache/huggingface` inside the container. Every rebuild re-downloads about 2 GB, and every failed download silently degrades search quality (see Task 5.1).

**Fix:** Add a named volume to both the `backend` and `worker` services:

  worker:

    build: ./backend

    volumes:

      \- ./backend:/app

      \- hf\_cache:/root/.cache/huggingface     \# ← ADD

    ...

volumes:

  postgres\_data:

  redis\_data:

  minio\_data:

  hf\_cache:                                    \# ← ADD

---

### Phase 2 exit criteria

1. Upload a small text-based PDF through the UI.  
2. `docker compose logs -f worker` shows `Successfully ingested document <uuid> with N chunks`.  
3. `SELECT status FROM documents ORDER BY created_at DESC LIMIT 1;` returns `indexed`.  
4. `SELECT count(*) FROM chunks;` is greater than zero.  
5. Searching for a phrase you know is in the PDF returns that document.

---

## Phase 3 — One schema, one migration chain

**Goal:** `alembic upgrade head` succeeds on a completely empty database and produces a schema that matches the models. **Estimated effort:** 2 days **Depends on:** Phase 1 **Branch:** `fix/phase-3-schema`

### 3.1 Understand the problem before you touch anything

There are currently **three** conflicting definitions of the same database, and all three disagree:

|  | `chunks` primary key | `tenant_id`? | Vector size | Tables defined |
| :---- | :---- | :---- | :---- | :---- |
| **SQLAlchemy models** | `id` | no (until Task 2.1) | 1024 | 12 |
| **Alembic migrations** | `chunk_id` | yes | 1536 → 1024 | 3 |
| **`migrations/init.sql`** | `id` | no | 1024 | 8 |

On top of that:

- The first migration calls `sa.JSONB()`. That attribute **does not exist** in SQLAlchemy 2.x (it lives at `sqlalchemy.dialects.postgresql.JSONB`). `alembic upgrade head` therefore fails on its first statement — and `alembic upgrade head` is the backend container's start command.  
- The migrations only ever create three tables: `documents`, `chunks`, `folders`. Nine tables — `tenants`, `users`, `document_versions`, `metadata`, `permissions`, `audit_logs`, `chat_sessions`, `chat_messages`, `api_logs` — are never created at all. So even after fixing `sa.JSONB`, the second migration's `add_column('document_versions', ...)` fails on a table that does not exist.  
- `migrations/init.sql` contains all the Row-Level Security policies, but it is **not mounted in `docker-compose.yml` and not referenced by Alembic**, so it never runs. This is why RLS does nothing (Phase 4).

**The decision:** the SQLAlchemy models are the single source of truth. Everything else gets regenerated from them.

> ⚠️ **Confirm with your lead before starting.** This procedure destroys the existing schema. It is correct for development and demo environments. If any deployed instance holds data someone cares about, stop and ask for a data migration plan instead.

### [x] 3.2 Fix `migrations/env.py` first

**File:** `backend/migrations/env.py` **Problem:** Lines 24–31 import only eight models. `Folder`, `ChatSession`, `ChatMessage` and `ApiLog` are missing, so Alembic's autogenerate would not see those four tables and would silently omit them — and then try to *drop* them if they already existed.

**Fix:** Replace lines 22–33 with:

\# add your model's MetaData object here for 'autogenerate' support.

\# app.models.\_\_init\_\_ imports every model, which registers them all on Base.metadata.

from app.database import Base

import app.models  \# noqa: F401  (import for side effects — registers all models)

target\_metadata \= Base.metadata

Also add dotenv loading near the top so Alembic works when run outside Docker:

from dotenv import load\_dotenv

load\_dotenv()

(`python-dotenv` is a transitive dependency of `pydantic-settings`, but add `python-dotenv>=1.0.0` to `requirements.txt` explicitly so it is not accidental.)

**Verify:**

cd backend && python \-c "

import app.models

from app.database import Base

print(sorted(Base.metadata.tables.keys()))

"

You must see all twelve: `api_logs`, `audit_logs`, `chat_messages`, `chat_sessions`, `chunks`, `document_versions`, `documents`, `folders`, `metadata`, `permissions`, `tenants`, `users`.

---

### [x] 3.3 Squash the migration history

Complete Tasks 2.1, 2.3, 2.4, 2.5 and 3.2 **before** this step — the generated migration bakes in whatever the models say at this moment.

\# 1\. Delete every existing migration

rm backend/migrations/versions/\*.py

\# 2\. Start Postgres only, on a clean volume

docker compose down \-v

docker compose up \-d postgres

sleep 10

\# 3\. Enable the required extensions (Alembic autogenerate cannot do this itself)

docker compose exec postgres psql \-U docsearch \-d docsearch \-c \\

  'CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS pg\_trgm;'

\# 4\. Generate the new baseline migration

cd backend

export POSTGRES\_URL='postgresql+asyncpg://docsearch:\<your-password\>@localhost:5432/docsearch'

alembic revision \--autogenerate \-m "baseline schema from models"

**Now read the generated file line by line.** Autogenerate is a helpful assistant, not an oracle. Check specifically that:

- All twelve tables are created.  
- `chunks.embedding` is `Vector(1024)`.  
- `chunks.id` is the primary key (not `chunk_id`).  
- `chunks.tenant_id` exists with a foreign key to `tenants.id`.  
- `users.full_name` exists.  
- `users` has the `uq_users_email` unique constraint.

Then add the extension creation to the very top of the migration's `upgrade()` so a fresh database works without the manual step 3:

def upgrade() \-\> None:

    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.execute('CREATE EXTENSION IF NOT EXISTS pg\_trgm')

    \# ... autogenerated statements follow ...

---

### [x] 3.4 Hand-write a second migration for what autogenerate cannot see

Alembic does not know about generated columns, HNSW vector indexes, or GIN indexes. Without these, keyword search breaks and vector search does a slow full scan of every row.

cd backend && alembic revision \-m "search indexes and generated tsvector"

Fill in the new file:

def upgrade() \-\> None:

    \# Full-text search column, maintained automatically by Postgres.

    \# The keyword leg of hybrid search reads chunks.content\_tsv.

    op.execute("""

        ALTER TABLE chunks

        ADD COLUMN IF NOT EXISTS content\_tsv tsvector

        GENERATED ALWAYS AS (to\_tsvector('english', content)) STORED

    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx\_chunks\_content\_tsv ON chunks USING GIN (content\_tsv)")

    \# Approximate-nearest-neighbour index for the vector leg.

    \# Without this, every search scans every chunk row.

    op.execute("""

        CREATE INDEX IF NOT EXISTS idx\_chunks\_embedding

        ON chunks USING hnsw (embedding vector\_cosine\_ops)

        WITH (m \= 16, ef\_construction \= 64\)

    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx\_metadata\_value ON metadata USING GIN (value)")

    op.execute("CREATE INDEX IF NOT EXISTS idx\_audit\_logs\_details ON audit\_logs USING GIN (details)")

def downgrade() \-\> None:

    op.execute("DROP INDEX IF EXISTS idx\_audit\_logs\_details")

    op.execute("DROP INDEX IF EXISTS idx\_metadata\_value")

    op.execute("DROP INDEX IF EXISTS idx\_chunks\_embedding")

    op.execute("DROP INDEX IF EXISTS idx\_chunks\_content\_tsv")

    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS content\_tsv")

> If autogenerate already emitted a `content_tsv` column (because the model declares it as `Computed`), delete it from the baseline migration and let this one own it. Only one migration should create it.

---

### [x] 3.5 Make `init_db.py` safe, or delete it

**File:** `backend/app/init_db.py` **Problem:** Three separate faults. It begins with `DROP SCHEMA public CASCADE` — an unguarded, irreversible data-destroying statement sitting in the application package. It seeds a user with `role='user'`, which is not a member of the `user_role` enum (`admin`, `editor`, `viewer`). And it inserts a `full_name` column that (before Task 2.3) did not exist.

**Recommended fix — delete the file.** Alembic now owns schema creation, and `sign_up()` creates the first real tenant and user.

**If your lead wants to keep a dev seeding script,** rename it to `backend/scripts/seed_dev_data.py`, remove the `DROP SCHEMA` and `CREATE SCHEMA` lines entirely, remove the `create_all` call, and fix the seed to use a valid role and a properly hashed password:

from app.services.auth\_service import hash\_password

await conn.execute(text("""

    INSERT INTO tenants (id, name, created\_at)

    VALUES ('00000000-0000-0000-0000-000000000001', 'Default Tenant', NOW())

    ON CONFLICT (id) DO NOTHING

"""))

await conn.execute(text("""

    INSERT INTO users (id, tenant\_id, email, full\_name, password\_hash, role, created\_at)

    VALUES (

        '00000000-0000-0000-0000-000000000002',

        '00000000-0000-0000-0000-000000000001',

        'admin@example.com', 'Default Admin', :pw, 'admin', NOW()

    )

    ON CONFLICT (id) DO NOTHING

"""), {"pw": hash\_password("changeme")})

Note the column is `password_hash`, not `hashed_password` — the model maps the Python attribute `hashed_password` onto the SQL column `password_hash`.

---

### [x] 3.6 Delete `migrations/init.sql`

**File:** `backend/migrations/init.sql` **Problem:** It is never executed by anything, and it disagrees with the models. Leaving it in the repository guarantees that the next developer will read it, believe it, and be wrong.

Its only genuinely valuable content is the RLS policy block. **Copy that into the Phase 4 migration first**, then delete the file.

---

### Phase 3 exit criteria

docker compose down \-v          \# completely fresh volumes

docker compose up \--build

1. The backend container starts and stays up.  
2. `http://localhost:8000/api/docs` loads and lists every endpoint group.  
3. `docker compose exec postgres psql -U docsearch -d docsearch -c '\dt'` shows all twelve tables.  
4. You can sign up a new user through the UI, log in, create a folder, and upload a document.  
5. `alembic downgrade base && alembic upgrade head` runs cleanly (proves both directions work).

---

## Phase 4 — Close the tenant boundary

**Goal:** A user of Tenant A cannot obtain any data belonging to Tenant B, and cannot take over another user's account. **Estimated effort:** 3 days **Depends on:** Phase 3 **Branch:** `fix/phase-4-security`

> Take this phase seriously. The documentation and the demo script both tell customers that tenant isolation is enforced by the database. Right now that statement is not true. Tasks 4.1 and 4.2 are the most important work in this entire document.

### [x] 4.1 Fix the password-reset token leak — do this first

**File:** `backend/app/api/v1/auth.py`, the `/forgot-password` endpoint **Problem:** The endpoint returns the password reset token **in the HTTP response body**:

return ForgotPasswordResponse(

    message="Password reset token generated successfully...",

    reset\_token=reset\_token           \# ← anyone who knows an email gets this

)

Anyone who knows a user's email address can call `/forgot-password`, read the token straight out of the JSON response, and immediately POST it to `/reset-password` with a password of their choosing. That is unauthenticated, single-request account takeover for any account in the system, including administrators.

**Fix, in three parts:**

1. **Never return the token.** Always respond with the same generic message, whether or not the email exists:

@router.post('/forgot-password', response\_model=ForgotPasswordResponse)

async def forgot\_password(body: ForgotPasswordRequest, db: AsyncSession \= Depends(get\_db)):

    stmt \= select(User).where(User.email \== body.email)

    user \= (await db.execute(stmt)).scalar\_one\_or\_none()

    if user:

        reset\_token \= create\_password\_reset\_token(body.email)

        await send\_password\_reset\_email(user.email, reset\_token)   \# Task 4.1.2

        await log\_action(db, user.id, user.tenant\_id, "auth.forgot\_password")

        await db.commit()

    \# Identical response in both branches — do not leak whether the account exists.

    return ForgotPasswordResponse(

        message="If an account with that email exists, a reset link has been sent."

    )

2. **Remove `reset_token` from the schema.** In `backend/app/schemas/auth.py`, delete the `reset_token: str | None = None` field from `ForgotPasswordResponse`. If the field does not exist, it cannot leak.  
     
3. **Send the token by email.** If SMTP is not available yet, create `backend/app/services/email_service.py` with a stub that **logs the token at DEBUG level on the server only** and raises a clear `NotImplementedError` when `APP_ENV=production`:

async def send\_password\_reset\_email(email: str, token: str) \-\> None:

    if settings.app\_env \== "production":

        raise NotImplementedError("SMTP not configured — refusing to send reset tokens in production")

    logger.debug("DEV ONLY — password reset token for %s: %s", email, token)

4. **Update the frontend.** `frontend/app/(auth)/forgot-password/page.tsx` currently reads the token from the response. Change it to show the confirmation message only.

**Verify:**

curl \-s \-X POST localhost:8000/api/v1/auth/forgot-password \\

  \-H 'Content-Type: application/json' \-d '{"email":"admin@example.com"}' | grep \-i token

\# Must return nothing.

---

### [x] 4.2 Scope the admin analytics endpoints to one tenant

**File:** `backend/app/api/v1/admin.py` **Problem:** Neither `/analytics` nor `/api-analytics` filters by tenant. They return global document counts, storage totals, per-tenant storage breakdowns, and **the full names and email addresses of the top uploaders across every customer organisation**.

This is made worse by `sign_up()`, which assigns `UserRole.admin` to every self-registered user. So the `require_admin` check protects nothing — every user in the system is an admin of their own tenant, and therefore passes it.

The endpoint currently returns HTTP 500 because of the `Chunk.chunk_id` bug (Task 2.2). **Fixing that bug turns a crash into a live cross-tenant data leak.** These must ship together.

**Fix, in two parts:**

1. **Add a tenant filter to every query in both endpoints.** Extract the tenant at the top of each function and thread it through:

@router.get('/analytics')

async def get\_admin\_analytics(

    current\_user: TokenPayload \= Depends(require\_tenant\_access),

    db: AsyncSession \= Depends(get\_db\_with\_tenant),      \# ← tenant-scoped session

):

    require\_admin(current\_user)

    tenant\_id \= uuid.UUID(current\_user.tenant\_id)        \# ← ADD

    total\_users \= (await db.execute(

        select(func.count(User.id)).where(User.tenant\_id \== tenant\_id)   \# ← ADD where

    )).scalar() or 0

    total\_documents \= (await db.execute(

        select(func.count(Document.id))

        .where(Document.tenant\_id \== tenant\_id, Document.is\_trashed \== False)

    )).scalar() or 0

    \# ... and so on for EVERY query in the function

Work through the file methodically. There are fifteen queries in `/analytics` and ten in `/api-analytics`. **Every one needs a tenant filter.** For `ApiLog`, filter on `ApiLog.tenant_id == tenant_id`.

2. **Delete the `total_tenants` and `storage_per_tenant` sections entirely.** There is no tenant-scoped version of "storage across all tenants" — the concept itself is cross-tenant. Remove the queries and the corresponding keys from the response dictionary, then remove the matching UI blocks from `frontend/app/admin/page.tsx`.

>   
> **Follow-up for your lead:** the product needs to decide whether "platform operator" is a distinct role from "tenant admin". If a real cross-tenant dashboard is wanted, it needs a separate `superadmin` role, a separate route prefix, and its own access control — not a flag on the ordinary admin endpoint. Raise this; do not decide it yourself.

**Verify:** Create two tenants with different documents. Log in as each and call `/api/v1/admin/analytics`. Each must see only its own counts.

---

### [x] 4.3 Turn Row-Level Security on

**Problem:** All the RLS policies exist in `migrations/init.sql`, which never runs. `set_tenant_context()` sets a PostgreSQL session variable (`app.current_tenant_id`) that no policy reads. The database currently applies zero isolation of its own; every guarantee rests on developers remembering to write `WHERE tenant_id = ...` by hand.

RLS is defence in depth: even if a query forgets its filter, the database refuses to return the rows.

**Fix:** Create a migration that applies the policies:

cd backend && alembic revision \-m "enable row level security"

TABLES \= \["documents", "document\_versions", "chunks", "metadata",

          "audit\_logs", "permissions", "folders", "chat\_sessions"\]

def upgrade() \-\> None:

    for t in TABLES:

        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")

        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")

    \# Tables with a direct tenant\_id column

    for t in \["documents", "chunks", "folders", "chat\_sessions"\]:

        op.execute(f"DROP POLICY IF EXISTS {t}\_tenant\_isolation ON {t}")

        op.execute(f"""

            CREATE POLICY {t}\_tenant\_isolation ON {t}

            USING (tenant\_id \= current\_setting('app.current\_tenant\_id', true)::uuid)

            WITH CHECK (tenant\_id \= current\_setting('app.current\_tenant\_id', true)::uuid)

        """)

    \# Tables reached via document\_id

    for t in \["document\_versions", "metadata"\]:

        op.execute(f"DROP POLICY IF EXISTS {t}\_tenant\_isolation ON {t}")

        op.execute(f"""

            CREATE POLICY {t}\_tenant\_isolation ON {t}

            USING (document\_id IN (

                SELECT id FROM documents

                WHERE tenant\_id \= current\_setting('app.current\_tenant\_id', true)::uuid

            ))

        """)

    op.execute("DROP POLICY IF EXISTS audit\_logs\_tenant\_isolation ON audit\_logs")

    op.execute("""

        CREATE POLICY audit\_logs\_tenant\_isolation ON audit\_logs

        USING (actor\_tenant\_id \= current\_setting('app.current\_tenant\_id', true)::uuid)

    """)

def downgrade() \-\> None:

    for t in TABLES:

        op.execute(f"DROP POLICY IF EXISTS {t}\_tenant\_isolation ON {t}")

        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")

Note the `WITH CHECK` clause — `USING` controls what you can read, `WITH CHECK` controls what you can write. Without both, a tenant could insert rows tagged with another tenant's id.

> **Important:** turn RLS on only *after* Task 4.4, or every endpoint that uses a plain session will start returning empty results and you will not know why.

---

### [x] 4.4 Use the tenant-scoped session everywhere

**Problem:** Only three of roughly thirty endpoints use `get_db_with_tenant` (the dependency that calls `set_tenant_context`). Everything in `folders.py`, `chat.py`, `admin.py`, and most of `documents.py` uses the plain `get_db`.

**Fix:** In `folders.py`, `chat.py`, `admin.py` and `documents.py`, replace every occurrence of:

db: AsyncSession \= Depends(get\_db)

with

db: AsyncSession \= Depends(get\_db\_with\_tenant)

Update the imports in each file accordingly. Note `folders.py` currently imports `get_db` from `app.database` rather than `app.deps` — change it to `from app.deps import get_db_with_tenant, require_tenant_access`.

**Leave the four unauthenticated auth endpoints alone** — `/login`, `/sign-up`, `/forgot-password` and `/reset-password` have no tenant context yet by definition, and must keep using plain `get_db`.

**Verify:**

cd backend && grep \-rn "Depends(get\_db)" app/api/v1/

\# Should only match login, sign-up, forgot-password and reset-password.

---

### [x] 4.5 Fix the tenant context lost at commit

**File:** `backend/app/database.py` **Problem:** `set_config('app.current_tenant_id', :tenant_id, true)` — the third argument `true` means *transaction-local*. The setting is discarded at the next `COMMIT`. `document_service.upload_document()` commits partway through, so every query after that commit runs with **no tenant context**, and with RLS enabled (Task 4.3) will return nothing.

**Fix:** Make the setting session-local instead of transaction-local by changing `true` to `false`:

async def set\_tenant\_context(session: AsyncSession, tenant\_id: str) \-\> None:

    """Set the tenant id for RLS. Session-scoped so it survives commits

    within a single request; the connection is returned to the pool at

    end of request, and the next request sets its own value."""

    await session.execute(

        text("SELECT set\_config('app.current\_tenant\_id', :tenant\_id, false)"),

        {"tenant\_id": str(tenant\_id)}

    )

> **Ask your lead to review this one.** Session-scoped settings persist on a pooled connection. Because `get_db_with_tenant` sets the value at the start of every request that uses it, the value is always overwritten before use — but any endpoint that uses plain `get_db` could inherit a stale value from a previous request. That is precisely why Task 4.4 (use the scoped session everywhere) must be completed alongside this one. An alternative, safer design is to reset the setting in the `finally` block of `get_db`; discuss which approach the team prefers.

---

### [x] 4.6 Set the tenant context in the Celery worker

**File:** `backend/app/tasks/worker.py` **Problem:** The worker writes chunks and metadata using `AsyncSessionLocal()` directly and never calls `set_tenant_context`. Once `FORCE ROW LEVEL SECURITY` is on (Task 4.3), every one of those inserts will be rejected.

**Fix:** Inside `_ingest_document_task_async`, immediately after opening each session:

from app.database import AsyncSessionLocal, set\_tenant\_context

async with AsyncSessionLocal() as db:

    await set\_tenant\_context(db, str(tenant\_id))     \# ← ADD

    async with db.begin():

        ...

Do this in **both** places — the main transaction and the failure-cleanup block.

---

### [x] 4.7 Harden the refresh token

**File:** `backend/app/api/v1/auth.py`, `backend/app/services/auth_service.py` **Problem:** `/refresh` accepts any structurally valid token, including a short-lived *access* token. There is no `type` claim distinguishing the two, so an access token can be exchanged for fresh tokens indefinitely — which defeats the point of a 15-minute access token expiry. The `jti` claim is generated but never stored or checked, so there is no way to revoke anything.

**Fix (minimum):** Add a `type` claim and verify it.

In `auth_service.py`:

def create\_access\_token(...):

    to\_encode \= {..., "type": "access"}

def create\_refresh\_token(...):

    to\_encode \= {..., "type": "refresh"}

Add `type: str = "access"` to `TokenPayload` in `schemas/auth.py`, then in the `/refresh` endpoint:

payload \= verify\_token(refresh\_token)

if payload.type \!= "refresh":

    raise HTTPException(status\_code=401, detail="Not a refresh token")

And in `deps.get_current_user`, reject refresh tokens used as access tokens:

payload \= verify\_token(credentials.credentials)

if payload.type \!= "access":

    raise HTTPException(status\_code=401, detail="Invalid token type")

**Fix (follow-up ticket, do not attempt now):** store `jti` values in Redis with a TTL to support real logout and revocation. Write the ticket; do not build it in this phase.

---

### [x] 4.8 Apply the rate limiter

**File:** `backend/app/main.py` and the route files **Problem:** `Limiter` is instantiated and registered on `app.state`, and `RATE_LIMIT_PER_USER` is configurable — but no route ever uses it. The setting is decorative.

**Fix:** Apply the decorator to the endpoints that cost money or are attack surfaces — `/auth/login`, `/auth/sign-up`, `/auth/forgot-password`, `/search/`, `/chat/sessions/{id}/messages`:

from app.main import limiter          \# or move \`limiter\` into its own module to avoid a circular import

@router.post('/login', response\_model=TokenResponse)

@limiter.limit(settings.rate\_limit\_per\_user)

async def login(request: Request, body: LoginRequest, db: AsyncSession \= Depends(get\_db)):

    ...

slowapi requires the endpoint to accept a parameter named exactly `request: Request`. Add it where it is missing. To avoid a circular import, move `limiter = Limiter(...)` into a new `backend/app/limiter.py` and import it from both `main.py` and the routers.

---

### [x] 4.9 Reject weak JWT secrets in production

**File:** `backend/app/config.py` **Problem:** `jwt_secret_key` defaults to the literal string `'secret'`. If `.env` is missing or the variable is unset in production, every token in the system is forgeable by anyone.

**Fix:** Add a validator to the `Settings` class:

from pydantic import model\_validator

@model\_validator(mode="after")

def \_check\_production\_secrets(self):

    if self.app\_env \== "production":

        if self.jwt\_secret\_key in ("secret", "", "generate\_with\_openssl\_rand\_hex\_32"):

            raise ValueError("JWT\_SECRET\_KEY must be set to a strong random value in production")

        if len(self.jwt\_secret\_key) \< 32:

            raise ValueError("JWT\_SECRET\_KEY must be at least 32 characters")

    return self

Failing loudly at startup is much better than running insecurely.

---

### Phase 4 exit criteria

Write these as automated tests in `backend/tests/test_tenant_isolation.py` — this is the single most valuable test file in the project:

1. Create Tenant A and Tenant B, each with a user and an uploaded document.  
2. As A's user, `GET /api/v1/documents` returns only A's document.  
3. As A's user, `GET /api/v1/documents/{B_document_id}` returns 404, not 200\.  
4. As A's user, `POST /api/v1/search` for a phrase unique to B's document returns zero results.  
5. As A's user, `GET /api/v1/admin/analytics` reports A's document count, not the global total.  
6. `POST /api/v1/auth/forgot-password` never includes a token in the response body.  
7. An access token rejected at `POST /api/v1/auth/refresh`.

---

## Phase 5 — Stop the AI layer fabricating data

**Goal:** When an AI provider fails, the system says so. It never invents content and passes it off as extracted. **Estimated effort:** 2 days **Depends on:** Phase 3 **Branch:** `fix/phase-5-ai-honesty`

> These are the most dangerous bugs in the codebase, because nothing crashes. The system looks perfectly healthy while producing fabricated output. A user has no way to tell the difference.

### [x] 5.1 The fake embeddings

**File:** `backend/app/ai/providers/bgem3_provider.py` **Problem:** Read `generate_bgem3_vector()` carefully:

def generate\_bgem3\_vector(text: str, dimensions: int \= 1024\) \-\> List\[float\]:

    seed \= int.from\_bytes(hashlib.sha256(text.encode('utf-8')).digest()\[:4\], 'big')

    rng \= np.random.RandomState(seed)

    vec \= rng.randn(dimensions)

    return (vec / norm).tolist()

This is a **random vector seeded by the hash of the text**. It is deterministic and correctly 1024-dimensional, so nothing downstream complains — but it carries no meaning whatsoever. "Annual leave policy" and "holiday entitlement rules" get completely unrelated vectors. Semantic search degrades to noise.

`embed()` falls back to this silently whenever `SentenceTransformer` cannot load — no API key needed, no model download available, out of memory, offline container. The only trace is one `WARNING` line in the logs.

**Fix:** Make the failure loud and visible.

class EmbeddingUnavailableError(RuntimeError):

    """Raised when no real embedding model is available."""

class BGEM3EmbeddingProvider(EmbeddingProvider):

    def \_\_init\_\_(self, model\_name: str \= "BAAI/bge-m3", allow\_fake: bool \= False):

        self.model\_name \= model\_name

        self.\_dimensions \= 1024

        self.\_model \= None

        self.\_allow\_fake \= allow\_fake      \# only ever true in unit tests

    def \_load\_model(self):

        if self.\_model is None:

            from sentence\_transformers import SentenceTransformer

            logger.info("Loading local BGE-M3 embedding model (%s)...", self.model\_name)

            self.\_model \= SentenceTransformer(self.model\_name)   \# let it raise

            logger.info("BGE-M3 loaded successfully.")

    async def embed(self, texts: List\[str\]) \-\> List\[List\[float\]\]:

        if not texts:

            return \[\]

        try:

            self.\_load\_model()

        except Exception as e:

            if self.\_allow\_fake:

                logger.warning("Using FAKE deterministic vectors — test mode only")

                return \[generate\_bgem3\_vector(t, self.\_dimensions) for t in texts\]

            raise EmbeddingUnavailableError(

                f"BGE-M3 embedding model unavailable: {e}. "

                "Install sentence-transformers, or set AI\_EMBED\_PROVIDER to a configured API provider."

            ) from e

        ...

Rename `generate_bgem3_vector` to `_generate_fake_test_vector` and add a docstring saying in plain words that it is not an embedding.

The worker already catches ingest exceptions and marks the document `failed` — which is exactly the right outcome. The user sees a failed document instead of a document that quietly returns wrong search results forever.

---

### [x] 5.2 The fabricated metadata

**File:** `backend/app/ai/providers/groq_provider.py` **Problem:** When every Groq API key fails, `complete()` returns hardcoded JSON:

if "Extract the following metadata" in last\_msg:

    return '{"title": "Ingested Document", "author": "Groq LLM System", "date": "2026-07-21", ...}'

The worker parses that and writes it into the `metadata` table with `source="llm"` and `confidence_score=0.9`. **Invented data, persisted as though a model extracted it, labelled as 90% confident.** Anyone auditing the system would reasonably call this data fabrication.

`FallbackLLMProvider.complete()` in `ai/factory.py` does the same for search summaries, returning canned prose as an "AI summary".

**Fix:**

1. In `groq_provider.py`, delete the entire fallback block and raise instead:

logger.error("All %d Groq API key(s) failed or hit rate limits.", max\_attempts)

raise last\_exception or RuntimeError("All Groq API keys failed")

2. In `ai/factory.py`, `FallbackLLMProvider.complete()` should re-raise once the secondary provider has also failed, rather than returning canned text:

except Exception as inner\_e:

    logger.warning("Secondary LLM provider failed: %s", inner\_e)

    raise

3. Handle the failure at each call site with an honest message.  
     
   In `worker.py`'s `extract_metadata()` — return `{}` and log. Missing metadata is fine; the document still indexes and remains searchable, which is the important part.  
     
   In `search_service.py` — the existing `try/except` around summary generation already does the right thing, but change the message so it does not imply an AI wrote it:

except Exception as e:

    logger.warning("AI summary unavailable: %s", e)

    summary \= (

        f"Found {len(final\_results)} matching document(s) for '{query}'. "

        "AI summary is temporarily unavailable — the excerpts below are unedited source text."

    )

---

### [x] 5.3 Do not index placeholder text as content

**Files:** `backend/app/ocr/extractor.py`, `backend/app/tasks/worker.py` **Problem:** When extraction fails, `extractor.py` returns strings like `"Scanned page 1 of document report.pdf"` or `"Scanned PDF document: report.pdf"`. The worker then embeds and indexes those as if they were document content. Worse, `worker.py` lines 77–79 create a deliberate fallback chunk of `f"Document: {filename}"` when no text was extracted at all.

The result: a document with zero readable content still shows up as `indexed` and appears in search results with a meaningless snippet.

**Fix:** Mark the extraction quality explicitly. In `extractor.py`, add an `"extraction_failed": True` key to any page dictionary that contains only a placeholder. Then in `worker.py`:

if not chunks or all(p.get("extraction\_failed") for p in pages):

    raise ValueError(

        "No readable text could be extracted from this document. "

        "It may be a scanned image requiring an OCR provider "

        "(set AI\_OCR\_PROVIDER=gcv or llamaparse)."

    )

The existing exception handler marks the document `failed` and shows the reason. That is honest and actionable — the user learns they need to enable OCR.

---

### [x] 5.4 Surface AI health in the API

**File:** new — `backend/app/api/v1/health.py` **Problem:** There is no way to find out whether the embedding model actually loaded without reading container logs.

**Fix:** Add a health endpoint that reports what is really configured and working:

@router.get('/health')

async def health\_check():

    checks \= {}

    try:

        provider \= get\_embed\_provider()

        vec \= await provider.embed(\["health check"\])

        checks\["embeddings"\] \= {

            "status": "ok",

            "provider": type(provider).\_\_name\_\_,

            "dimensions": len(vec\[0\]),

        }

    except Exception as e:

        checks\["embeddings"\] \= {"status": "error", "detail": str(e)}

    \# repeat for redis, postgres, minio

    overall \= "ok" if all(c\["status"\] \== "ok" for c in checks.values()) else "degraded"

    return {"status": overall, "checks": checks}

Register it in `router.py` without authentication (it exposes no data) and add a Docker healthcheck for the backend service pointing at it.

---

### Phase 5 exit criteria

1. With `sentence-transformers` uninstalled, uploading a document marks it `failed` with a clear message — it does not silently index fake vectors.  
2. With all LLM keys blank, search still returns results, and the summary explicitly says the AI summary is unavailable.  
3. No row in the `metadata` table ever contains `"Groq LLM System"`.  
4. `GET /api/v1/health` reports `degraded` when the embedding model cannot load.

---

## Phase 6 — Search correctness and quality

**Goal:** Filters work, deleted documents stay hidden, and results are not duplicated. **Estimated effort:** 2 days **Depends on:** Phase 3 **Branch:** `fix/phase-6-search`

### [x] 6.1 Fix the broken filter parameters

**File:** `backend/app/services/search_service.py` **Problem:** Two related bugs in the same function.

First, the code builds a `params` dictionary containing all the filter bind values (lines 66–98), and then **never passes it** — line 128 executes with only `query` and `tenant_id`. Any request that includes a filter therefore fails with a missing bind parameter error.

Second, `filter_str` is interpolated into `kw_sql` but **not** into `vec_sql`. Even if the binds were passed, filters would only constrain the keyword half of a hybrid search — the vector half would happily return documents the user explicitly filtered out.

**Fix:** Add `filter_str` to the vector query's `WHERE` clause and pass the full `params` dict to both executions:

vec\_sql \= text(f"""

    SELECT c.id, c.content, c.page\_number, c.chunk\_index, d.title, d.id as doc\_id, v.s3\_path,

           1 \- (c.embedding \<=\> CAST(:query\_embedding AS vector)) as vector\_score

    FROM chunks c

    JOIN documents d ON c.document\_id \= d.id

    LEFT JOIN document\_versions v ON v.id \= d.current\_version\_id

    WHERE d.tenant\_id \= :tenant\_id

      AND d.status \= 'indexed'

      AND d.is\_trashed \= false

      {filter\_str}

    ORDER BY c.embedding \<=\> CAST(:query\_embedding AS vector)

    LIMIT 20

""")

vec\_params \= {\*\*params, "query\_embedding": q\_emb\_str, "tenant\_id": str(tenant\_id)}

vec\_res \= await db.execute(vec\_sql, vec\_params)

kw\_params \= {\*\*params, "tenant\_id": str(tenant\_id)}

kw\_res \= await db.execute(kw\_sql, kw\_params)

Note `params` already contains `query` and `tenant_id`; setting `tenant_id` to the string form explicitly avoids a UUID/text comparison mismatch.

---

### [x] 6.2 Hide trashed documents from search

**File:** `backend/app/services/search_service.py` **Problem:** Neither the vector query nor the keyword query filters on `is_trashed`. A user "deletes" a document in the Drive UI, and it keeps appearing in search results with a working download link.

**Fix:** Add `AND d.is_trashed = false` to both queries' `WHERE` clauses. (Task 6.1's snippet already includes it for the vector leg — do the same for `kw_sql`.)

---

### [x] 6.3 Fix the inconsistent version join

**File:** `backend/app/services/search_service.py` **Problem:** The two queries join `document_versions` differently:

- vector leg: `LEFT JOIN document_versions v ON v.document_id = d.id`  
- keyword leg: `LEFT JOIN document_versions v ON c.version_id = v.id`

The first joins on *document*, so once a document has two versions, every chunk is returned twice — inflating result counts and corrupting RRF ranking, since duplicate rows occupy multiple rank positions.

**Fix:** Use the same join in both, keyed on the document's current version:

LEFT JOIN document\_versions v ON v.id \= d.current\_version\_id

This also guarantees the download link always points at the current version rather than an arbitrary old one.

---

### [x] 6.4 Populate the result metadata

**File:** `backend/app/services/search_service.py` **Problem:** Every `SearchResult` is constructed with `metadata={}`. The schema, the product spec and the UI all promise extracted metadata (document type, urgency, dates) on each result. `MetadataItem` is imported at the top of the file and never used.

**Fix:** After assembling `final_results`, fetch metadata for the matched documents in one query and attach it:

doc\_ids \= list({r.document\_id for r in final\_results})

if doc\_ids:

    meta\_rows \= (await db.execute(

        select(MetadataItem.document\_id, MetadataItem.key, MetadataItem.value)

        .where(MetadataItem.document\_id.in\_(doc\_ids))

    )).all()

    by\_doc: dict \= {}

    for doc\_id, key, value in meta\_rows:

        \# values are stored as {"v": \<scalar\>} or as a raw dict/list

        flat \= value.get("v") if isinstance(value, dict) and set(value) \== {"v"} else value

        by\_doc.setdefault(doc\_id, {})\[key\] \= flat

    for r in final\_results:

        r.metadata \= by\_doc.get(r.document\_id, {})

One query for all results — do **not** query inside the loop.

---

### [x] 6.5 Cap the snippet length

**File:** `backend/app/services/search_service.py` **Problem:** `snippet=row.content` returns the entire chunk — up to 512 tokens, roughly 2 KB — for every result. Ten results is 20 KB of JSON per search, most of it never displayed.

**Fix:** Truncate around the match:

def \_make\_snippet(content: str, max\_chars: int \= 400\) \-\> str:

    if len(content) \<= max\_chars:

        return content

    return content\[:max\_chars\].rsplit(" ", 1)\[0\] \+ "…"

Keep sending the full text to the LLM for the summary — only the API response snippet is truncated.

---

### [x] 6.6 Write down the caching limitation

**File:** `backend/app/services/cache_service.py` **Problem:** `generate_cache_key()` hashes the exact query string. The architecture document calls this "semantic caching (Layer 0)". It is not semantic — "annual leave policy" and "what is the annual leave policy" produce different keys and both miss.

**Fix for now:** Do not build semantic caching. Just correct the comment and the documentation so nobody is misled, and add a cache-invalidation call so that newly indexed documents are not hidden behind a stale five-minute cache entry — `invalidate_tenant_cache()` already exists in the module but is never called. Call it at the end of a successful ingest.

Open a ticket for real semantic caching (embed the query, look up nearest cached query above a similarity threshold) as a future enhancement.

---

### Phase 6 exit criteria

1. Searching with `{"doc_type": "invoice"}` returns only invoices and does not error.  
2. A trashed document does not appear in search results.  
3. A document with two versions appears once, not twice.  
4. Search results carry a populated `metadata` object.  
5. Uploading a new document makes it searchable immediately, without a five-minute cache wait.

---

## Phase 7 — Hardening, tests and documentation

**Goal:** The project is safe for another developer to pick up. **Estimated effort:** 3 days **Branch:** `fix/phase-7-hardening`

### 7.1 Fix the API logging middleware

**File:** `backend/app/api_logging_middleware.py` **Problem:** The comment says "fire-and-forget, don't block response", but the code opens a database session and `await`s a `COMMIT` **before returning the response**. Every API call now costs an extra database round trip, including `GET /` health polls. It also calls `verify_token()` on every request, duplicating work the auth dependency already did.

**Fix:** Push the write into a background task so the response returns first:

import asyncio

async def \_write\_log(\*\*kwargs):

    try:

        async with AsyncSessionLocal() as session:

            session.add(ApiLog(\*\*kwargs))

            await session.commit()

    except Exception as e:

        logger.warning("Failed to log API call: %s", e)

\# in dispatch(), replace the inline session block with:

asyncio.create\_task(\_write\_log(

    method=request.method, path=path, status\_code=response.status\_code,

    response\_time\_ms=round(elapsed\_ms, 2), user\_id=user\_id, tenant\_id=tenant\_id,

    ip\_address=ip\_address, user\_agent=user\_agent,

))

return response

Also add a retention policy — `api_logs` grows without bound. A nightly Celery beat task deleting rows older than 30 days is enough.

---

### 7.2 Add file upload validation

**File:** `backend/app/services/document_service.py` **Problem:** `upload_document()` calls `await file.read()`, loading the entire file into memory with **no size limit and no content-type check**. A single large upload can exhaust the container's memory.

**Fix:** Add limits to config and enforce them before reading:

\# config.py

max\_upload\_size\_mb: int \= 50

allowed\_upload\_extensions: List\[str\] \= \[

    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",

    "csv", "txt", "md", "rtf", "json", "jpg", "jpeg", "png",

\]

\# document\_service.py, at the top of upload\_document()

ext \= (file.filename or "").rsplit(".", 1)\[-1\].lower()

if ext not in settings.allowed\_upload\_extensions:

    raise HTTPException(400, f"File type '.{ext}' is not supported")

file\_bytes \= await file.read()

max\_bytes \= settings.max\_upload\_size\_mb \* 1024 \* 1024

if len(file\_bytes) \> max\_bytes:

    raise HTTPException(413, f"File exceeds the {settings.max\_upload\_size\_mb} MB limit")

---

### 7.3 Prevent folder cycles

**File:** `backend/app/services/folder_service.py` **Problem:** `update_folder()` checks only that a folder is not its own parent. Moving folder A into its own child B creates a detached cycle — both disappear from the tree and can never be recovered through the UI.

**Fix:** Walk up from the proposed new parent and reject if you meet the folder being moved:

async def \_is\_descendant(db, candidate\_id: UUID, ancestor\_id: UUID) \-\> bool:

    current \= candidate\_id

    for \_ in range(100):                 \# depth guard against pre-existing cycles

        if current is None:

            return False

        if current \== ancestor\_id:

            return True

        folder \= await db.get(Folder, current)

        if folder is None:

            return False

        current \= folder.parent\_id

    return True                          \# suspiciously deep — treat as a cycle

\# in update\_folder(), before assigning the new parent:

if await \_is\_descendant(db, folder\_in.parent\_id, folder\_id):

    raise HTTPException(400, "Cannot move a folder into one of its own subfolders")

---

### 7.4 Bulk upload should not swallow every error

**File:** `backend/app/services/document_service.py` **Problem:** `upload_documents_bulk()` catches every exception per file, increments a counter, and reports only a number. A user uploading 50 files and getting "3 failed" has no way to learn which three or why.

**Fix:** Collect the failures and return them:

failures: List\[dict\] \= \[\]

for file in files:

    try:

        uploaded\_docs.append(await upload\_document(...))

    except Exception as err:

        logger.exception("Failed to upload %s", file.filename)

        failures.append({"filename": file.filename, "error": str(err)})

return BatchDocumentUploadResponse(

    documents=uploaded\_docs, total=len(files),

    succeeded=len(uploaded\_docs), failed=len(failures), failures=failures,

)

Add `failures: List[dict] = []` to `BatchDocumentUploadResponse` in `schemas/document.py` and show them in the upload UI.

---

### 7.5 Build a real test suite

**Current state:** four test files, two of which are connection smoke tests, and no test runner configured.

**Fix:** Add to `requirements.txt`:

pytest==8.3.3

pytest-asyncio==0.24.0

httpx==0.27.2

Create `backend/tests/conftest.py` with fixtures for a test database, an HTTP client, and two tenants with separate users. Then write, in priority order:

| File | What it covers |
| :---- | :---- |
| `test_tenant_isolation.py` | **Highest priority.** All seven Phase 4 exit criteria. |
| `test_auth.py` | Sign-up, login, refresh token type checks, no token in forgot-password response. |
| `test_ingestion.py` | Upload → chunks created → status `indexed`; a corrupt file marks `failed`. |
| `test_search.py` | Filters apply, trashed hidden, no duplicates, metadata populated. |
| `test_folders.py` | Create, move, cycle rejection, trash, permanent delete. |

Aim for the critical paths, not a coverage percentage. Do not spend time testing getters.

---

### 7.6 Add a CI pipeline

Create `.github/workflows/ci.yml` running on every push and pull request:

1. The four checks from §0.4 (conflict markers, py\_compile, pyflakes, tsc).  
2. `alembic upgrade head` against a throwaway Postgres service container.  
3. `pytest backend/tests/`.  
4. `npm run build` for the frontend.

Step 1 alone would have caught every Phase 1 bug before it reached `main`. Do this early in the phase, not at the end.

---

### 7.7 Correct the documentation

The seven files in `docs/` are genuinely good, which makes the inaccuracies more dangerous — a reader has no reason to doubt them.

| File | What to correct |
| :---- | :---- |
| `docs/SYSTEM_ARCHITECTURE.md` | §3.1 describes RLS as active. Only true after Task 4.3 — until then, add a "Not yet enabled" banner. |
| `docs/DEMO_PRESENTATION_GUIDE.md` | "Act 5: Row-Level Security & Tenant Data Isolation Proof" cannot currently be demonstrated. Do not present this act until Phase 4 ships. |
| `docs/SETUP_GUIDE.md` | Documents credentials `admin@example.com / changeme` that no seed actually creates. Fix after Task 3.5. |
| `docs/AI_PIPELINE_AND_MODELS.md` | Add a section documenting the failure behaviour of every provider — after Phase 5, "it raises" is the honest answer. |
| `README.md` | Update the Phase 2 roadmap; several items marked outstanding now exist. |

Add a `docs/KNOWN_LIMITATIONS.md` listing what is deliberately unfinished. That file is worth more to the next developer than another architecture diagram.

---

## Phase 8 — Desktop application (separate project)

**Status:** Not started. No Electron or Tauri scaffolding exists. The only step in this direction is the `webkitdirectory` folder-picker input at `frontend/app/drive/page.tsx` line 477, which performs a one-off browser folder upload — not a persistent OS-level permission grant.

**Do not begin this phase until Phases 1–6 are complete and merged.** Porting a codebase that cannot start would duplicate every bug in this document into a second target.

### 8.1 Why the current stack cannot simply be shipped

The project targets "downloadable on laptops and desktops, asks for folder permission, starts its core work". The current stack — PostgreSQL, Redis, Celery, MinIO, Docker Compose, six containers — is a server SaaS deployment. End users will not install Docker. Every one of those six moving parts needs a single-process equivalent.

### 8.2 Proposed architecture

| Concern | Server mode (today) | Desktop mode (proposed) |
| :---- | :---- | :---- |
| Shell | Browser at `localhost:3000` | **Tauri** wrapping the existing Next.js UI. Ships a \~10 MB binary versus Electron's \~150 MB, and gives a native folder-permission dialog for free. |
| Database | PostgreSQL \+ pgvector | **SQLite \+ sqlite-vec \+ FTS5.** Your RRF merge logic ports across unchanged — only the two SQL strings change. |
| Job queue | Celery \+ Redis | In-process worker thread plus a **`watchdog`** filesystem observer, so files dropped into the granted folder are ingested automatically. |
| Object storage | MinIO / S3 | The local filesystem. "Download URL" becomes "reveal in file manager". |
| Embeddings | BGE-M3 via sentence-transformers | Same model exported to **ONNX** via `fastembed`, so search works fully offline. |
| LLM summaries | Groq / OpenAI / Anthropic | Optional. Degrade to "excerpts only" with no key configured — which Phase 5 already implements correctly. |
| Auth | JWT, multi-tenant | Single local user behind a `DEPLOYMENT_MODE=desktop` flag. Keep the SaaS code path intact; do not fork the repository. |
| Packaging | `docker compose up` | Python backend bundled with **PyInstaller** as a Tauri sidecar; installers via the Tauri bundler. |

### 8.3 Suggested sequence

1. Introduce a `DEPLOYMENT_MODE` setting (`server` | `desktop`) and a storage abstraction so `storage_service` can back onto either S3 or the local filesystem.  
2. Add a SQLite implementation behind the same repository interface; get the test suite green against both backends.  
3. Replace Celery with an in-process queue when `DEPLOYMENT_MODE=desktop`.  
4. Add the `watchdog` folder watcher and the permission-grant flow.  

---

## Appendix A — Task summary

| # | Task | Phase | Priority | Est. | Status |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 1.1 | Merge conflict — `auth_service.py` | 1 | P0 | 30 m | Done [x] |
| 1.2 | Merge conflict — `pdfplumber_provider.py` | 1 | P0 | 30 m | Done [x] |
| 1.3 | Merge conflict — `api.ts` | 1 | P0 | 10 m | Done [x] |
| 1.4 | Rewrite `ingestion.py` | 1 | P0 | 2 h | Done [x] |
| 1.5 | CORS override | 1 | P1 | 20 m | Done [x] |
| 2.1 | `Chunk.tenant_id` | 2 | P0 | 30 m | Done [x] |
| 2.2 | `Chunk.chunk_id` → `id` | 2 | P0 | 15 m | Done [x] |
| 2.3 | `User.full_name` | 2 | P0 | 30 m | Done [x] |
| 2.4 | Tenant name uniqueness | 2 | P1 | 15 m | Done [x] |
| 2.5 | User email uniqueness | 2 | P1 | 20 m | Done [x] |
| 2.6 | Cache AI providers | 2 | P1 | 1 h | Done [x] |
| 2.7 | Persist model cache volume | 2 | P2 | 20 m | Done [x] |
| 3.2 | Fix `migrations/env.py` | 3 | P0 | 30 m | Done [x] |
| 3.3 | Squash migrations | 3 | P0 | 4 h | Done [x] |
| 3.4 | Index migration | 3 | P0 | 2 h | Done [x] |
| 3.5 | Fix or delete `init_db.py` | 3 | P1 | 1 h | Done [x] |
| 3.6 | Delete `init.sql` | 3 | P2 | 15 m | Done [x] |
| 4.1 | **Password reset token leak** | 4 | **P0** | 3 h | Done [x] |
| 4.2 | **Admin analytics tenant scoping** | 4 | **P0** | 4 h | Done [x] |
| 4.3 | Enable RLS | 4 | P0 | 3 h | Done [x] |
| 4.4 | Tenant-scoped session everywhere | 4 | P0 | 2 h | Done [x] |
| 4.5 | Tenant context lost at commit | 4 | P0 | 1 h | Done [x] |
| 4.6 | Worker tenant context | 4 | P0 | 1 h | Done [x] |
| 4.7 | Refresh token type claim | 4 | P1 | 2 h | Done [x] |
| 4.8 | Apply rate limiter | 4 | P1 | 2 h | Done [x] |
| 4.9 | Reject weak JWT secret | 4 | P1 | 1 h | Done [x] |
| 5.1 | Fake embeddings | 5 | P0 | 3 h | Done [x] |
| 5.2 | Fabricated metadata | 5 | P0 | 3 h | Done [x] |
| 5.3 | Placeholder text indexing | 5 | P1 | 2 h | Done [x] |
| 5.4 | Health endpoint | 5 | P1 | 2 h | Done [x] |
| 6.1 | Filter bind parameters | 6 | P1 | 2 h | Done [x] |
| 6.2 | Hide trashed from search | 6 | P1 | 30 m | Done [x] |
| 6.3 | Version join consistency | 6 | P1 | 1 h | Done [x] |
| 6.4 | Populate result metadata | 6 | P2 | 2 h | Done [x] |
| 6.5 | Cap snippet length | 6 | P2 | 1 h | Done [x] |
| 6.6 | Document cache limitation | 6 | P2 | 1 h | Done [x] |
| 7.1 | API logging middleware | 7 | P1 | 2 h | Done [x] |
| 7.2 | Upload validation | 7 | P1 | 2 h | Done [x] |
| 7.3 | Folder cycle prevention | 7 | P2 | 2 h | Done [x] |
| 7.4 | Bulk upload error reporting | 7 | P2 | 2 h | Done [x] |
| 7.5 | Test suite | 7 | P1 | 2 d | Done [x] |
| 7.6 | CI pipeline | 7 | P1 | 4 h | Done [x] |
| 7.7 | Documentation corrections | 7 | P2 | 4 h | Done [x] |

**Total for Phases 1–7:** roughly 13–15 working days.

---

## Appendix B — Escalate immediately if

- Any instruction in this document does not match what you see in the file. The code has moved; do not improvise.  
- A fix in Phases 1–3 requires changing the database schema in a way not described here.  
- You find any additional merge conflict markers — that means another bad merge landed, and someone senior needs to review the branch history.  
- Task 4.2 reveals that a real cross-tenant admin dashboard is a product requirement. That is a product decision, not an engineering one.  
- Anything in Phase 4 or 5 appears to be already exploited in a deployed environment. Report it the same day.

## Appendix C — Reference commands

\# Full clean restart

docker compose down \-v && docker compose up \--build

\# Backend logs only

docker compose logs \-f backend

\# Worker logs (watch ingestion here)

docker compose logs \-f worker

\# Database shell

docker compose exec postgres psql \-U docsearch \-d docsearch

\# Useful queries

\\dt                                                          \-- list tables

SELECT id, title, status FROM documents ORDER BY created\_at DESC LIMIT 10;

SELECT count(\*) FROM chunks;

SELECT key, value FROM metadata ORDER BY created\_at DESC LIMIT 20;

\# Redis shell

docker compose exec redis redis-cli \-a "$REDIS\_PASSWORD"

\# Migrations

cd backend

alembic current                     \# which migration is applied

alembic history \--verbose           \# full chain

alembic upgrade head

alembic downgrade \-1

\# Re-queue every failed document

docker compose exec worker python \-m app.tasks.reindex\_failed  
