# Module (d) — Entity & Knowledge Layer

SoW 3.4 · Status as of 2026-09-08, commit `e1af8ff` · See [ROADMAP.md](ROADMAP.md) for the whole-system picture.

- [x] **T10** — Property-graph schema
  Evidence: tier, status, confidence, creating actor or policy, evidence pointer. Migrations `0014`–`0017`, `0040`.

- [x] **T56** — Tiered linking — tiers 1–2 auto, tier 3 escrowed, tier 4 human-only
  Evidence: tier 4 is held regardless of how confident the machine is.

- [x] **T57** — Bulk threshold confirmation with a full audit trail
  Evidence: actor, threshold, corpus folder, policy version and batch ID recorded on every affected edge.

- [x] **T58** — Link reversibility; machine labels stay permanent
  Evidence: undo by batch ID; a later human confirmation never erases the original machine authorship label.

- [x] **T59** — Per-corpus calibration required before bulk acceptance
  Evidence: both bulk-confirm paths refuse until `is_corpus_calibrated()` passes.

**Watch, not open:** both cross-tenant bugs found in the D-2 security review were in this
module's API — one an exploitable read. D-2 itself is fixed (see [ROADMAP.md](ROADMAP.md)),
but this remains the newest large surface in the product and is worth the next dedicated
security read, not because anything here is currently broken.

**Open items in this module:** none.
