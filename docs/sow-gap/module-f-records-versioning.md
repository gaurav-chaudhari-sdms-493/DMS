# Module (f) — Records & Versioning

SoW 3.6 · Status as of 2026-09-08, commit `e1af8ff` · See [ROADMAP.md](ROADMAP.md) for the whole-system picture.

- [x] **T60** — Amendment chains, deterministically re-derivable current state
  Evidence: current state is derived on read, never stored — no mutable "current" column that could drift from its evidence.

- [x] **T61** — Legal-status layer
  Evidence: in force / set aside / under stay / superseded, computed from the amendment chain with `DISTINCT ON`.

- [x] **T62** — Entity and Property 360 view
  Evidence: `frontend/app/entities/page.tsx` imports and renders `RegionHighlightViewer` (line 21, 598) — a value on the 360 screen now opens its source page the same way the workbench and search citations already did. **Was "partial — doesn't reuse the region viewer" as of 04-Sep; now fixed.**

**Open items in this module:** none.
