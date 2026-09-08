# Module (h) — Governance & Audit

SoW 3.8 · Status as of 2026-09-08, commit `e1af8ff` · See [ROADMAP.md](ROADMAP.md) for the whole-system picture.

Carries the product's "evidence-grade" claim — the module the D-2 tenant-isolation finding
lived under.

- [x] **T34** — Drop the dead `permissions` table
  Evidence: migration `0012`, real RBAC built in its place.

- [x] **T50** — RBAC for six personas
  Evidence: records officer, operator, department head, legal counsel, IT admin, auditor, plus department scoping.

- [x] **T63** — Tamper-evident audit — append-only, hash chains, integrity checker
  Evidence: SHA-256 chain per tenant; an advisory lock stops the chain forking under concurrency; append-only enforced by grants.

- [x] **T64** — WORM archival with retention lock
  Evidence: S3 Object Lock in `COMPLIANCE` mode, called from `document_service.py:461`.

- [ ] **T65** — Section 63 certificate generation — **blocked on A3**
  The generator works — hash, algorithm, dual signature blocks (`backend/app/services/certificate_service.py`, verified live in `backend/tests/test_certificate.py`) — and stamps a red `DRAFT TEMPLATE — NOT A VALID SECTION 63 CERTIFICATE` banner on every output until legal counsel review clears the wording.

- [x] **T66** — Retention policy engine per record class
  Evidence: classes in migration `0024` under signed D-7; the purge runs in Celery beat with its window read from config.

- [x] **T67** — Verified-layer boundary enforced at the query layer
  Evidence: `gather_evidence_package()` with a `certificate` mode excluding unconfirmed facts and edges, per D-8 — one enforcement point, not scattered per call site.

**The D-2 finding, resolved.** Row-level security was previously enabled and doing
nothing — the application connected as a Postgres superuser (`rolbypassrls = t`) and no
route set `app.current_tenant_id`. **Fixed:** a restricted, non-superuser `dms_app` role
(migration `0046_restricted_app_role.py`) plus `AppSessionLocal` in `backend/app/database.py`,
which sets `app.current_tenant_id` per session via `establish_tenant_context()`. A related
regression found this pass — `db.commit()` could silently drop that tenant context before
the next statement on the same connection, reopening the same class of gap on 10 call
sites — was also found and fixed; see `backend/tests/test_commit_then_refresh_under_rls.py`.

**Open items in this module:** 1, external (T65 — see [ROADMAP.md](ROADMAP.md#the-10-open-tasks-grouped-by-what-blocks-them)).
