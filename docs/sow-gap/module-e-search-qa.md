# Module (e) — Search & Q&A

SoW 3.5 · Status as of 2026-09-08, commit `e1af8ff` · See [ROADMAP.md](ROADMAP.md) for the whole-system picture.

- [x] **T70** — Uncited-answer refusal gate (hard rule 1)
  Evidence: drops uncited claims and returns nothing when the excerpts don't support the query — a refusal, not a low-confidence answer.

- [x] **T71** — Citation click-through to a highlighted region
  Evidence: `frontend/components/search/CitationModal.tsx` → `CitationPageViewerImpl.tsx`, reusing the workbench's own region viewer.

- [x] **T72** — pg_trgm leg added to search
  Evidence: GIN trigram index in migration `0029`; threshold seeded in `0030`.

- [x] **T73** — Search over extracted structured records, not just chunk text
  Evidence: `backend/app/services/search_service.py:419-441`.

- [x] **T74** — Immediate metadata-level findability on ingest
  Evidence: documents still processing return by title with a "still processing" snippet.

- [x] **T75** — Devanagari indexing correctness
  Evidence: migration `0013` adds `content_tsv_simple` so the index and query stop disagreeing.

**Open items in this module:** none.
