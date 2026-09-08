# Module (c) — Human Verification Workbench

SoW 3.3 · Status as of 2026-09-08, commit `e1af8ff` · See [ROADMAP.md](ROADMAP.md) for the whole-system picture.

- [x] **T51** — Two-lane model plus per-row state machine
  Evidence: enum enforced at the DB level; transitions enforced in the service layer, not just the UI.

- [x] **T52** — Adjudication queues with claim and release
  Evidence: five categories — low confidence, handwritten, marginalia, join mismatch, stitch ambiguous.

- [x] **T53** — Click-through from field to highlighted source region, including visual crooked-scan correction
  Evidence: `frontend/components/common/RegionHighlightViewerImpl.tsx` on pdf.js, wired at `frontend/app/workbench/page.tsx:739`. **Was "skew stored, not visually corrected" as of 04-Sep** — now fixed: `frontend/components/common/RegionViewerImpl.tsx` applies a real canvas rotate+skew transform (`ctx.rotate`, `ctx.transform` with the stored skew angle), not a CSS approximation.

- [x] **T54** — Keyboard-first navigation, batch accept above a threshold
  Evidence: ↑/↓, A/Enter, C, R, H; threshold read from `sys_dg_config`.

- [x] **T55** — Hard-rule tests
  Evidence: no promotion without an actor; no handwritten row in a bulk confirm; only `in_review` can reach `verified`.

**Open items in this module:** none.
