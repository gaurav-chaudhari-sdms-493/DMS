# GSD Technical Specification: VeritasDocs v0.3 / v1 Build

## 1. System Overview & Baseline Context
- **Repository Branch**: `dev` @ `5d8e1cb`
- **Scope Baseline**: VeritasDocs v1 SoW v0.3 / CR-001 (71 Tasks, 11 Modules, 9 Pending Decisions, 6 External Assumptions)
- **Primary Objective**: Upgrade DMS to evidence-grade processing pipeline with page-region provenance, hostile-format handlers, human verification workbench, entity property graph, tamper-evident audit, and air-gapped local model execution.

---

## 2. Decision & Governance Ledger

| Decision | Area | Description / Resolution Status | Blocking Tasks |
|---|---|---|---|
| **D-1** | Container Model | Collapse recursive folders to 2-level Workspace → Project model (§3.10) or raise CR | `T10`, `T50`, `T94` |
| **D-2** | Tenant Isolation | Ratify row-level security (RLS) vs schema-per-tenant | Module (j) |
| **D-3** | Token Lifetime | Adjust JWT token lifespan (from 30-day default to standard short-lived tokens + refresh) | Security Baseline / W0 |
| **D-4** | Accuracy Tolerance | M1 ground truth accuracy tolerance thresholds | M1 Exit / Phase W1 |
| **D-5** | Confidence Policy | Per-template vs global confidence calibration | `T20`, `T51` |
| **D-6** | Local Models | Legal clearance for Surya GPL licensing in on-prem distribution | `T90` |
| **D-7** | Retention Classes | Define data retention classes and rules | `T66` |
| **D-8** | Escrow Links | Define policy for escrowed identity links in Section 63 exports | `T65`, `T67` |
| **D-9** | Built Drive Scope | Settle scope status of built drive UI features (folders, star, trash, offline shell) | Architecture Baseline |

---

## 3. Modular Phase Specifications (Waves W0 – W5)

### Phase W0: Foundations & Data Provenance (Wave W0)
- **Module 0**: Foundations & Engineering Standards
- **Core Requirements**:
  - `T01`: Rename tables, FKs, indexes to `{module}_dg_*` format; update `search_service.py`, `chat_service.py`, RLS policies.
  - `T02`: Create `sys_dg_config` table and typed, cached accessor with documented defaults.
  - `T03`: Move hardcoded thresholds (relevance 0.15, RRF k=60, chunk 512/64, retention 30d) into `sys_dg_config`.
  - `T04`: Add provenance columns (`page_number`, `bounding_box` coordinates) to extracted facts; enforce non-null constraint at write time.
  - `T05`: Carry word bounding boxes from `pdfplumber`/OCR extractor through chunker to fact writer.
  - `T06`: Draft D2 coordinate standard (origin top-left, normalized `[x0, y0, x1, y1]`, page-size normalization, rotation handling).
  - `T07`: Append-only audit logging for document/folder mutations, views, downloads.
  - `T08`: Service boundary actor identity requirement (reject unauthenticated mutations).
  - `T09`: D2 Technical Architecture Specification.
  - `T10`: PostgreSQL property-graph baseline schema (`entity_dg_nodes`, `entity_dg_edges`).
  - `T33`: Fix silent image OCR extraction success bug.
  - `D-3`: Configurable short-lived JWT token security.
- **Verification Gate**:
  - Migration runs cleanly; models pass unit tests.
  - Fact extraction writes non-null page number and bounding box coordinates for every fact.
  - Hardcoded threshold references replaced by `sys_dg_config` calls.

---

### Phase W1: Ingestion & Core Processing IP (Wave W1)
- **Modules**: (a) Ingestion & Connectors, (b) Document Processing Pipeline
- **Core Requirements**:
  - `T21`: Devanagari/Marathi OCR (`lang='mar+eng'`, Tesseract traineddata).
  - `T20`: Real per-field confidence scoring algorithm.
  - `T23`: Document classification stage + unclassified queue.
  - `T24`: Template registry keyed by statutory form and era.
  - `T25`: Seed templates (Basmath Form A 1974, Washim Form B 2004).
  - `T22`: VLM extraction pipeline pass.
  - `T26`: **Hostile Handler 1**: Multi-page spread join (serial/row ordinality join, parity check, mismatch routing).
  - `T27`: **Hostile Handler 2**: Ditto-chain expansion (per-column expansion, chain-break rules, >10 row/page spanning).
  - `T28`: **Hostile Handler 3**: Continuation-row merge (blank-serial row backward merging).
  - `T29`: **Hostile Handler 4**: Blob-cell parser & unit normalization (sqm, sqft, hectares, gunthas, Akker).
  - `T30`: Marginalia & degraded text adjudication routing.
  - `T31` / `T32`: Regression test corpus & baseline accuracy report.
  - `T40`: Connector abstraction class & port HTTP upload.
  - `T41`: Ingest mandatory pass (PDF/A-2b, original preservation, retry, failure alerts).
  - `T42`-`T44`: Watched folder/FTP, Email-in, and Scanner connectors.
  - `T34`: Clean up / wire `permissions` table.
- **Verification Gate**:
  - Four hostile handlers pass synthetic & real document test suites.
  - Marathi OCR extracts Devanagari text cleanly from sample extracts.
  - Unified connector abstraction processes uploads idempotently with provenance.

---

### Phase W2: Human Verification Workbench & Access RBAC (Wave W2)
- **Modules**: (c) Verification Workbench, (h) Governance (RBAC)
- **Core Requirements**:
  - `T50`: 6-persona RBAC (Records Officer, Operator/Adjudicator, Dept Head, Legal Counsel, IT Admin, External Auditor) with Project/Collection scoping.
  - `T51`: Two-lane data state machine (`machine` → `in-review` → `human-verified`).
  - `T52`: Adjudication Queues (marginalia, join mismatches, low confidence, handwritten) with claim/release locking.
  - `T53`: Bounding-box click-through overlay mapping field values to highlighted PDF canvas regions.
  - `T54`: Keyboard-first operator navigation & batch-accept workflow.
  - `T55`: Hard verification rules (promotion requires actor event; handwritten content requires human confirmation).
- **Verification Gate**:
  - Promotion without an actor event raises permission error.
  - UI renders highlighted bounding boxes over PDF viewer upon field click.

---

### Phase W3: Knowledge Graph, Records & Audit Chain (Wave W3)
- **Modules**: (d) Entity Layer, (f) Records & Versioning, (h) Governance & Audit
- **Core Requirements**:
  - `T56`: Tiered entity linking engine (Tiers 1-2 auto-commit, Tier 3 escrowed identity, Tier 4 legal human-only).
  - `T57`-`T59`: Bulk threshold confirmation, link reversibility, threshold calibration protocol.
  - `T60`: Record amendment chains (base record → amendment sequence → derived current state).
  - `T61`: Legal status tracking (`in_force`, `set_aside`, `under_stay`, `superseded`).
  - `T62`: Entity & Property 360-degree aggregated views with source page click-through.
  - `T63`: Tamper-evident audit chain with append-only verification (`prev_hash` + `event_hash`).
  - `T64`: WORM retention lock integration.
  - `T65`: Section 63 Certificate generator (SHA-256 digest, dual signature blocks).
  - `T66`-`T67`: Retention policy engine and verified-layer query boundary enforcement.
- **Verification Gate**:
  - Tampering with any audit row is immediately flagged by integrity checker.
  - Re-derivation of current record state from base + amendment chain matches expected current view.

---

### Phase W4: Search Refinement, Reports & Data Operations (Wave W4)
- **Modules**: (e) Search & Q&A, (g) Reports & Analytics, (i) Data Operations, Connectors
- **Core Requirements**:
  - `T70`: Uncited-answer refusal gate (refuse grounded answer when grounding is weak or un-cited).
  - `T71`: Citation click-through highlighting exact source bounding box on document viewer.
  - `T72`: Add `pg_trgm` trigram index and query leg.
  - `T73`: Search over extracted structured records.
  - `T74`: Immediate metadata-level search findability upon ingest.
  - `T75`: Devanagari `tsvector` indexing correctness (`marathi`/`simple` parsing alignment).
  - `T45`-`T47`: Enterprise connectors (Google Drive OAuth/Changes API, SharePoint Graph delta sync, NIC e-Office).
  - `T76`-`T77`: Corpus completeness/reconciliation dashboard & exportable summary reports.
  - `T78`: Audited export engine (CSV, JSON, XLSX, PDF/A).
  - `T79`: Duplicate detection (SHA-256 + fuzzy rescan matching).
  - `T80`: Audited bulk edit engine with preview and bounded undo.
  - `T81`: Subscription metering and licensing enforcement engine.
- **Verification Gate**:
  - Ungrounded Q&A queries trigger clean refusal response.
  - Trigram search matches fuzzy/misspelled queries.

---

### Phase W5: Local VLM, Air-Gapped Egress & Shipping (Wave W5)
- **Modules**: (j) Admin & Deployment, Shipping
- **Core Requirements**:
  - `T90`: Local VLM provider implementation (`Qwen2.5-VL-7B-Instruct` via vLLM/Ollama + Surya/PaddleOCR).
  - `T91`: Fail-closed model provider toggle (no silent fallback to external API).
  - `T92`: Egress-zero verification script and CI pipeline check.
  - `T93`: Helm charts and air-gapped runbook installation scripts.
  - `T94`: Project/Collection container level enforcement in API and schema.
  - `T95`: Bilingual localization (EN + MR switcher, Devanagari digits).
  - `T96`: WCAG 2.1 AA / GIGW 3.0 accessibility audit & CI integration.
  - `T97`: Performance pass on high volume corpus.
  - `T98` / `T99`: Test suite coverage threshold & security hardening.
- **Verification Gate**:
  - `verify_egress_zero.py` passes with 0 outbound network calls.
  - Local VLM executes OCR and extraction offline.
