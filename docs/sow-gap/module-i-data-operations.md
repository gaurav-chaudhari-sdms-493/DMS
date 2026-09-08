# Module (i) — Data Operations

SoW 3.9 · Status as of 2026-09-08, commit `e1af8ff` · See [ROADMAP.md](ROADMAP.md) for the whole-system picture.

- [x] **T78** — Export — CSV, JSON, XLSX, PDF, PDF/A, audited
  Evidence: all five formats, content-hashed, refuses to run without an actor.

- [x] **T79** — Duplicate detection — hash-based plus fuzzy
  Evidence: SHA-256 exact match at capture; embedding-cosine candidates written during ingestion (migration `0042`, `backend/app/tasks/worker.py:301-330`).

- [x] **T80** — Bulk edit — preview, per-row audit, bounded undo, cannot mark verified
  Evidence: real `dry_run` preview; undo reads the audit log as its source of truth; status demoted to `in_review` on every edit, by construction.

**Open items in this module:** none.
