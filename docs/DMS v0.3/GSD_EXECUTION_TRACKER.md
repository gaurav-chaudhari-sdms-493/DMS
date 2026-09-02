# VeritasDocs v0.3 / v1 GSD Execution Tracker

## Context & State Summary
- **Target Specification**: [GSD_SPEC_VERITASDOCS_V0.3.md](file:///home/stark/JetBrainsProjects/DMS/docs/DMS%20v0.3/GSD_SPEC_VERITASDOCS_V0.3.md)
- **Baseline Branch**: `dev` @ `5d8e1cb`
- **Total Tasks**: 71 tasks across 11 modules
- **Current Active Wave**: **Phase W0: Foundations & Data Provenance** `[PENDING_APPROVAL]`

---

## Phase Execution Overview

- [ ] **Phase W0: Foundations & Provenance (W0)** `[READY]`
  - [ ] `T01` Rename DB tables, FKs, indexes to `{module}_dg_*` format.
  - [ ] `T02` Create `sys_dg_config` table and typed, cached accessor with defaults.
  - [ ] `T03` Move hardcoded thresholds (relevance 0.15, RRF k=60, chunk 512/64, retention 30d) into `sys_dg_config`.
  - [ ] `T04` Add provenance columns (`page_number`, `bounding_box` coordinates) to facts (non-null at write).
  - [ ] `T05` Carry word bounding boxes from `pdfplumber`/OCR extractor through chunker to fact writer.
  - [ ] `T06` Draft D2 Technical Architecture coordinate standard.
  - [ ] `T07` Add audit event logging on view, download, mutate document/folder paths.
  - [ ] `T08` Enforce actor identity requirement at service boundary.
  - [ ] `T09` Draft D2 Architecture Spec.
  - [ ] `T10` Create PostgreSQL property-graph schema (`entity_dg_nodes`, `entity_dg_edges`).
  - [ ] `T33` Fix silent OCR failure bug on image extraction error.
  - [ ] `D-3` Configure production JWT token lifespan and refresh rotation.

- [ ] **Phase W1: Connectors & Core IP Handlers** `[PENDING]`
- [ ] **Phase W2: Verification Workbench & Access RBAC** `[PENDING]`
- [ ] **Phase W3: Knowledge Graph, Records & Audit Chain** `[PENDING]`
- [ ] **Phase W4: Search Refinement, Reports & Data Ops** `[PENDING]`
- [ ] **Phase W5: Local VLM, Air-Gapped Egress & Shipping** `[PENDING]`

---

## Detailed Task Checklist & Progress Log

### Phase W0: Foundations & Provenance (W0)

- [ ] **T01: Rename DB Tables to `{module}_dg_*` Standard**
  - Target Files: `backend/app/models/`, `backend/app/services/search_service.py`, `backend/app/services/chat_service.py`
  - Action: Update SQLAlchemy table names & raw SQL queries to `{module}_dg_*` standard.
  - Verification: Run migration & verify backend models pass imports cleanly.

- [ ] **T02 & T03: `sys_dg_config` Table & Threshold Accessor**
  - Target Files: `backend/app/models/sys_config.py`, `backend/app/services/sys_config_service.py`, `backend/app/config.py`
  - Action: Build config table with cached accessor for relevance (0.15), RRF k (60), chunk sizes (512/64), retention (30d).
  - Verification: Test config fallback and override via API/service tests.

- [ ] **T04 & T05: Provenance Bounding-Box Coordinates in Pipeline**
  - Target Files: `backend/app/pipeline/extractor.py`, `backend/app/pipeline/chunker.py`, `backend/app/models/document.py`
  - Action: Preserve `pdfplumber`/OCR word bounding boxes through chunking step into fact table.
  - Verification: `pytest backend/tests/test_provenance_schema.py` asserts non-null page number and coordinates.

- [ ] **T06: D2 Coordinate Contract Standard**
  - Target Files: `docs/DMS v0.3/D2_COORDINATE_CONTRACT.md`
  - Action: Define standard `[x0, y0, x1, y1]` top-left relative coordinate format, rotation, and normalization rules.
  - Verification: Review contract document.

- [ ] **T07 & T08: Mutation Audit Events & Actor Identity Guard**
  - Target Files: `backend/app/api_logging_middleware.py`, `backend/app/deps.py`
  - Action: Audit write/view/download events and reject unauthenticated mutations.
  - Verification: Assert unauthorized endpoints reject mutations with 401/403.

- [ ] **T10: PostgreSQL Property-Graph Schema**
  - Target Files: `backend/app/models/entity_graph.py`
  - Action: Define `entity_dg_nodes` and `entity_dg_edges` tables.
  - Verification: Test node and edge insertion queries.

- [ ] **T33 & D-3: Silent OCR Fix & Short-Lived JWT Security**
  - Target Files: `backend/app/pipeline/extractor.py`, `backend/app/config.py`
  - Action: Set `extraction_failed` on unreadable OCR; configure short-lived JWT lifetime + refresh token.
  - Verification: Test failed image OCR handling & JWT token expiration.

---

## State Log & Verification Records

| Timestamp | Phase | Task | Status | Output / Test Result |
|---|---|---|---|---|
| 2026-08-20 | Setup | GSD Spec & Tracker Setup | Completed | Created `GSD_SPEC_VERITASDOCS_V0.3.md` & `GSD_EXECUTION_TRACKER.md` |
