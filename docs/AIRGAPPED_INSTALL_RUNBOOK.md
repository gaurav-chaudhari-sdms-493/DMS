# VeritasDocs — Helm Install Runbook (T93)

This runbook installs VeritasDocs on Kubernetes using the chart at
`helm/veritasdocs/`. It covers two profiles:

- **SaaS profile** (`values.yaml`) — the AI providers call external APIs
  (OpenAI/Anthropic/Groq/Gemini/Cohere), same as the default `docker-compose.yml` setup.
- **Air-gapped profile** (`values-airgapped.yaml`) — `AIR_GAPPED=true`. The
  backend/worker refuse (not silently skip) any AI/OCR call that would
  reach an external API.

## Read this before you start: what "air-gapped" actually covers today

Section 11 of `build_design.txt` describes a fully local install: a local
VLM (Qwen2.5-VL-7B) and local OCR (PaddleOCR/Surya/Docling) instead of
cloud APIs, a fail-closed toggle, and an egress-zero check (backlog
T90/T91/T92). **Only part of that exists in this codebase right now:**

| Surface | Local implementation? | Under `AIR_GAPPED=true` |
|---|---|---|
| Embeddings | Yes — `bgem3` (in-process `sentence_transformers`) | Works |
| Reranking | Yes — `bgem3` cross-encoder | Works |
| OCR | Yes — `pdfplumber`, and now `paddleocr` (T90) with real Devanagari/Marathi support | Works |
| LLM (chat, search answers) | **No** — only Groq/OpenAI/Anthropic exist | Refuses to start (`AirGappedViolation`) |
| VLM (document field extraction) | **No** — only Gemini exists; `QwenVLMProvider` exists as unverified scaffolding (no GPU to validate it), not wired into the active config | Refuses to start (`AirGappedViolation`) |

This chart and its `values-airgapped.yaml` profile deploy a fail-closed
install that is honest about that gap: it will not silently call an
external LLM/VLM API, but it also cannot serve chat or search-answer
generation fully offline, and cannot run VLM-based document field
extraction (as opposed to plain OCR text extraction, which now works
locally via `paddleocr`) until backlog **T90**'s VLM half — a real,
GPU-verified local Qwen2.5-VL provider — is finished.

**T92** (egress-zero verification) is now partially built: `app/ai/egress_guard.py`
patches httpx's transport when `AIR_GAPPED=true`, blocking any outbound
request to the six known external AI provider hosts at the network layer
— independent of, and in addition to, `enforce_local()`'s factory-level
check. It's covered by `backend/tests/test_egress_guard.py`, which runs
in CI on every push (`pytest tests/` in `.github/workflows/ci.yml`) —
that's the "CI coverage" half of T92's backlog line. What's still missing
is the *full* T92 scope build_design.txt describes: proving the complete
pipeline (ingest, check, search) runs entirely offline, which needs
T90's VLM half to exist. Ingestion + search *can* now run fully offline
for OCR-only extraction (no VLM field extraction) — see step 6a below.
Step 7 below is a live, one-time check of both guard layers on your
actual install, not a substitute for automated coverage.

If your install must serve chat, search-answer generation, or VLM-based
field extraction fully offline today, stop here and treat T90's VLM half
as a blocking prerequisite. If you only need OCR text extraction, plain
embedding-based search, and reranking offline, this runbook already
covers you — set `AI_OCR_PROVIDER=paddleocr` (see `values-airgapped.yaml`).

## 0. Prerequisites

| Tool | Notes |
|---|---|
| A Kubernetes cluster | v1.28+, with a default `StorageClass` (or set `global.storageClass`) |
| `kubectl` | matching your cluster's minor version |
| `helm` | v3.14+ |
| `docker` (or another OCI builder) | to build the backend/frontend images |
| A container registry reachable from the cluster | for air-gapped: an **offline/local** registry (e.g. `registry.airgapped.local:5000`) already mirrored into the target network — setting that registry up is outside this runbook's scope |

## 1. Build the application images

```bash
cd /path/to/DMS
docker build -t veritasdocs-backend:latest ./backend

# NEXT_PUBLIC_API_URL is inlined into the frontend's client bundle at
# build time (Next.js), not read at container start — pass the real
# external URL/ingress host you'll use for this install:
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://veritasdocs.your-domain \
  -t veritasdocs-frontend:latest ./frontend
```

## 2. Push (or mirror) images to your registry

**Hosted / SaaS profile**, with normal internet access to your registry:

```bash
docker tag veritasdocs-backend:latest  your-registry.example.com/veritasdocs-backend:latest
docker tag veritasdocs-frontend:latest your-registry.example.com/veritasdocs-frontend:latest
docker push your-registry.example.com/veritasdocs-backend:latest
docker push your-registry.example.com/veritasdocs-frontend:latest
```

**Air-gapped profile** — mirror the two images you just built *and* the
three upstream images the chart bundles (`ankane/pgvector:latest`,
`redis:7-alpine`, `minio/minio:latest`) into your offline registry. From a
machine that has internet access but not the air-gapped network:

```bash
docker pull ankane/pgvector:latest
docker pull redis:7-alpine
docker pull minio/minio:latest

docker save -o veritasdocs-images.tar \
  veritasdocs-backend:latest veritasdocs-frontend:latest \
  ankane/pgvector:latest redis:7-alpine minio/minio:latest
# carry veritasdocs-images.tar across the air gap by your approved
# physical/media transfer process, then on the inside:
docker load -i veritasdocs-images.tar
docker tag veritasdocs-backend:latest  registry.airgapped.local:5000/veritasdocs-backend:latest
docker tag veritasdocs-frontend:latest registry.airgapped.local:5000/veritasdocs-frontend:latest
docker tag ankane/pgvector:latest      registry.airgapped.local:5000/ankane/pgvector:latest
docker tag redis:7-alpine              registry.airgapped.local:5000/redis:7-alpine
docker tag minio/minio:latest          registry.airgapped.local:5000/minio/minio:latest
docker push registry.airgapped.local:5000/veritasdocs-backend:latest
docker push registry.airgapped.local:5000/veritasdocs-frontend:latest
docker push registry.airgapped.local:5000/ankane/pgvector:latest
docker push registry.airgapped.local:5000/redis:7-alpine
docker push registry.airgapped.local:5000/minio/minio:latest
```

`ankane/pgvector`/`redis`/`minio` are pulled by tag (`:latest`), not a
pinned digest — fine for this repo's own dev use, but if your mirroring
process requires reproducible, content-addressed images, re-tag by digest
(`docker inspect --format='{{index .RepoDigests 0}}' <image>`) before the
transfer and update `postgres.image`/`redis.image`/`minio.image` in your
values file accordingly. That hardening is a documented gap, not done here.

## 3. Write a private values file (do not commit it)

`values.yaml`'s `secrets:` block ships with placeholder passwords. Create
`my-install-values.yaml` (outside git, e.g. in a secrets manager or a
gitignored path) with at least:

```yaml
image:
  registry: "registry.airgapped.local:5000/"   # or your registry, with trailing slash

secrets:
  postgresPassword: "<generate a real secret>"
  redisPassword: "<generate a real secret>"
  jwtSecretKey: "<openssl rand -hex 32>"
  s3AccessKeyId: "<real value, not minioadmin>"
  s3SecretAccessKey: "<real value>"
  # SaaS profile only — leave blank for air-gapped:
  openaiApiKey: "..."
  cohereApiKey: "..."

ingress:
  enabled: true
  host: veritasdocs.your-domain
```

## 4. Install

**SaaS profile:**

```bash
helm install veritasdocs ./helm/veritasdocs \
  --create-namespace -n veritasdocs \
  -f my-install-values.yaml
```

**Air-gapped profile** — layer `values-airgapped.yaml` on top:

```bash
helm install veritasdocs ./helm/veritasdocs \
  --create-namespace -n veritasdocs \
  -f ./helm/veritasdocs/values-airgapped.yaml \
  -f my-install-values.yaml
```

This runs a pre-install Helm hook Job (`alembic upgrade head`) before any
application pod starts, then deploys Postgres, Redis, MinIO, backend,
worker, flower and frontend.

## 5. Verify the rollout

```bash
kubectl -n veritasdocs get pods
kubectl -n veritasdocs get jobs      # the migration Job should show Complete
```

All pods should reach `Running`/`Ready`. If a pod is stuck `Pending`,
check `global.storageClass` matches a StorageClass that actually exists
in your cluster (`kubectl get storageclass`).

Without an Ingress controller reachable yet, port-forward instead:

```bash
kubectl -n veritasdocs port-forward svc/veritasdocs-frontend 3000:3000 &
kubectl -n veritasdocs port-forward svc/veritasdocs-backend 8000:8000 &
```

Then open `http://localhost:3000` and `http://localhost:8000/api/docs`.
Sign up a user, create a folder, upload a document, and confirm search
returns results — this exercises Postgres, Redis, MinIO and the AI
provider path end to end.

The WORM archive bucket (`ensure_archive_bucket_exists()`) now runs
automatically on backend startup, alongside the main documents bucket —
no manual step needed. It creates the bucket with Object Lock enabled if
it doesn't already exist (best-effort: a failure here is logged, not
fatal, since WORM archival is an auxiliary evidence feature — see T64).
Object Lock can only be set at bucket-creation time, so if you ever see
`get_object_lock_configuration` report disabled on an existing
`s3ArchiveBucketName`, the fix is to recreate that bucket (it can't be
retrofitted), not to change code.

## 6. Air-gapped profile: confirm both fail-closed layers are actually live

`test_egress_guard.py` covers this in CI, but run it once live on your
actual install too, since CI can't see your real `AIR_GAPPED` env value:

```bash
# Layer 1 — factory-level: refuses before any client is even constructed
kubectl -n veritasdocs exec -it deploy/veritasdocs-backend -- python -c "
from app.ai.factory import get_llm_provider
try:
    get_llm_provider()
    print('FAIL: no exception raised — an external LLM call would have gone through')
except Exception as e:
    print(f'OK — refused: {e}')
"

# Layer 2 — network-level (T92): blocks the actual outbound request even
# if something bypassed layer 1. Should return in milliseconds, not
# time out — a real network attempt would take much longer or hang.
kubectl -n veritasdocs exec -it deploy/veritasdocs-backend -- python -c "
import time, httpx
from app.ai.airgapped import AirGappedViolation  # triggers the guard install on import
from app.ai.egress_guard import EgressBlockedError
start = time.monotonic()
try:
    httpx.get('https://api.openai.com/v1/models', timeout=5)
    print('FAIL: request was not blocked')
except EgressBlockedError as e:
    print(f'OK — blocked in {(time.monotonic()-start)*1000:.1f}ms: {e}')
"
```

Expected output: `OK — refused: AIR_GAPPED=true but 'LLM' is configured to
use '...', which calls an external API...`. If it prints the FAIL line
instead, do not consider this install air-gapped — stop and investigate
`AIR_GAPPED` in the backend pod's environment before going further
(`kubectl -n veritasdocs exec deploy/veritasdocs-backend -- env | grep AIR_GAPPED`).

Then confirm the paths that *should* work locally actually do, by
uploading and searching a document — embeddings (bgem3), reranking
(bgem3) and OCR (pdfplumber) all run in-process with no outbound call.

## 7. Uninstall

```bash
helm uninstall veritasdocs -n veritasdocs
kubectl delete pvc -n veritasdocs -l app.kubernetes.io/instance=veritasdocs   # StatefulSet volumes are not removed automatically
```

## What this chart intentionally leaves out

- The `sftp` and `mailserver` (Greenmail) services in `docker-compose.yml`
  are local demo fixtures for the connector walkthrough (a fixed
  single-tenant SFTP box and a fake local mailbox), not part of a
  production install — they are not in this chart.
- TLS termination/cert-manager wiring for the Ingress is left to your
  cluster's existing ingress controller conventions; `ingress.tls` only
  points at a `secretName` you provide.
