# Module (a) — Ingestion & Connector Framework

SoW 3.1 · Status as of 2026-09-08, commit `e1af8ff` · See [ROADMAP.md](ROADMAP.md) for the whole-system picture.

- [x] **T40** — Connector abstraction layer, one ingestion contract for every source
  Evidence: `backend/app/services/connector_base.py` — a typed `Connector` `Protocol`; adding a source never requires editing `main.py`.

- [x] **T41** — Mandatory-on-ingest set: PDF/A-2b with original kept, hash, provenance, safe retry, failure alerting
  Evidence: `backend/migrations/versions/0043_*.py`, `backend/app/tasks/worker.py:96-113` (PDF/A conversion, never blocks the original on failure); `backend/app/services/email_service.py::send_ingestion_failure_alert` (real email to the uploader — was logger-level only as of 04-Sep, now fixed).

- [x] **T42** — Watched folders and FTP/SFTP poller
  Evidence: folder watcher and SFTP poller, both with a stability grace period before a file is considered settled.

- [x] **T43** — Email-in via a dedicated mailbox
  Evidence: IMAP polling plus an inbound webhook.

- [x] **T44** — Scanner integration (TWAIN or network-scan folder drop)
  Evidence: `backend/app/services/scanner_connector.py`, `backend/app/api/v1/scanner_webhook.py` (registered in `backend/app/api/v1/router.py`), `docs/scanner_connector_setup.md`. A real authenticated webhook plus quality validation (sharpness/brightness/blank-page/skew checks), not just the watched-folder route the original plan assumed would be "almost certainly no new code."

- [ ] **T45** — Google Drive connector — **blocked on A8**
  Google restricted-scope verification never requested. No code exists; none is possible without the grant.

- [ ] **T46** — SharePoint connector — **blocked on A8**
  Microsoft Entra admin consent never requested. No code exists.

- [ ] **T47** — NIC e-Office connector — **blocked on A7**
  Integration access never requested. Gated at M4 exit by design — a fast-follow, never meant to be the sole release blocker.

**Open items in this module:** 3, all external (T45, T46, T47 — see [ROADMAP.md](ROADMAP.md#the-10-open-tasks-grouped-by-what-blocks-them)).
