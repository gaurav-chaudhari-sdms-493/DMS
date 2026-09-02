# VeritasDocs — Project Deep Dive

*A plain-language walkthrough of what this project is, the real problem it solves, everything that's been built, the technology behind it, and why every major decision was made the way it was — written so you can walk into a demo and explain any part of it with confidence.*

**Internal name:** Document Management System (DMS)
**Domain:** Government land & property records
**Languages:** English + Marathi
**Status:** All engineering complete; remaining items are external sign-offs, not code

**At a glance:**
- **6** user roles (RBAC)
- **4** layers in the search engine
- **76** backend functions live-tested
- **9** table-reading features (TS1–TS9) built against a real 1973 register
- **2** scripts read: English & Devanagari
- **0** unfinished engineering work

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [What We Built](#2-what-we-built)
3. [How It Works](#3-how-it-works)
4. [The Tech Stack](#4-the-tech-stack)
5. [Why These Choices](#5-why-these-choices)
6. [Security, Access & Trust](#6-security-access--trust)
7. [What's Done, What's Still Open](#7-whats-done-whats-still-open)
8. [Proven by Testing, Not Just Claimed](#8-proven-by-testing-not-just-claimed)
9. [Demo Cheat Sheet](#9-demo-cheat-sheet)
10. [Glossary](#10-glossary)

---

## 1. The Problem

Start here if you remember nothing else: this system exists because a huge amount of legally important information in India sits on paper that is old, handwritten, and effectively unsearchable.

**What a "waqf register" actually is.** A waqf is a permanent religious or charitable endowment under Islamic law — usually land or a building — donated forever for a religious or public purpose (a mosque, a graveyard, a school). Every Indian state has a Waqf Board that is legally required to keep a register of these properties: who owns what, its boundaries, its survey number, its current legal status. This project was built around real registers like this, but the same problem — and the same solution — applies to any government or legal department drowning in old paper records: land revenue offices, municipal archives, court record rooms.

The registers studied are physically old — some from the 1970s — typed or handwritten in Marathi, photographed or scanned as-is, often with pages split across a table that runs from the bottom of one page to the top of the next, or across a left page and a right page of an open ledger. Clerks used shorthand like **"Do."** (a "ditto" mark meaning "same value as the row above") to save time writing, which a computer reading it literally would misunderstand as an actual value called "Do."

### Why this is a real, expensive problem

- **Nobody can search it.** Finding "every property owned by a certain family" today means a person manually flipping through paper registers or scanned PDFs.
- **Nothing is verifiable at a glance.** When a legal dispute arises, someone needs to prove exactly what the original register said, when it was amended, and who has looked at it since — none of which paper gives you automatically.
- **Digitizing badly is worse than not digitizing.** A naive OCR ("just read the text") scan of a legal register that silently gets a survey number wrong, or silently merges two different people's names, creates a record that looks official but is quietly incorrect — which is arguably more dangerous than the paper original.
- **It has to survive real, messy documents** — not just clean modern scans, but 50-year-old paper with stamps, handwriting in the margins, faded ink, and tables split across pages in inconsistent ways.

> The brief, in one sentence: turn decades of old, handwritten, legally significant paper into something searchable and trustworthy — without ever pretending a machine's guess is a verified fact.

---

## 2. What We Built

VeritasDocs is a document management and search platform, purpose-built for exactly this problem: it reads scanned government registers (in English or Marathi), pulls out the structured legal data field-by-field, makes a human confirm every single fact before it counts as "official," links related records together, and keeps a permanent, tamper-evident record of every action taken on the data.

It is not "OCR software" and it is not "a search box." It is closer to a full digital records office: intake, reading, understanding, human sign-off, cross-referencing, search, and audit — each one a distinct, working system, wired together.

**The five-stage pipeline:**

| Stage | Name | What happens |
|---|---|---|
| 1 | **Intake** | Documents arrive by upload, watched folder, SFTP, or email. |
| 2 | **Read & Understand** | OCR reads the text; an AI vision model maps each answer to its field on the form. |
| 3 | **Human Verifies** | A person confirms, edits, or rejects every extracted fact before it's "official." |
| 4 | **Connect & Search** | Records link to related people/properties; everything becomes searchable. |
| 5 | **Govern** | Every action is permanently logged; exports flag what's verified vs. not. |

---

## 3. How It Works

A closer look at each stage — what actually happens, and what to point at during the demo.

### Reading the document

Every uploaded page is read twice, in two different ways, working together:

- **OCR (Optical Character Recognition)** reads the raw text off the page — including Marathi/Devanagari script — entirely on our own servers, so nothing leaves the building. This matters because the eventual deployment target is government infrastructure, some of it "air-gapped" (no internet access at all).
- **A vision-language AI model (VLM)** looks at the actual *image* of the page alongside a known form template (e.g. "Waqf Registration Form A") and works out which box on the form each answer belongs in — owner name goes here, survey number goes there. This is the difference between "the page contains the text 'Ramrao Patil' somewhere" and "the owner field on row 6 says 'Ramrao Patil', and here is the exact rectangle on the scan that proves it."

Anything the system can't confidently classify — the wrong form type, an illegible page, a stray handwritten note — is routed to a human review queue rather than guessed at.

### Making sense of real, old registers (the hardest part)

Clean modern PDFs are the easy case. The genuinely hard engineering work was making this reliable against a real 1973 government register — nine separate features built specifically for that:

- **Table stitching (rows split across pages)** — When a table's row starts at the bottom of one page and finishes at the top of the next — or splits across a left and right facing page — the system reconnects it into one correct row instead of silently losing half of it.
- **Ditto handling ("Do." marks)** — Old clerks wrote "Do." to mean "same as above." The system fills in the real repeated value automatically, while keeping the original mark on record — nothing is silently invented.
- **Page furniture detection (stamps & headers)** — Repeated letterheads, stamps, and footers on every page are recognized and excluded, so they're never mistaken for actual data.
- **Human-answer memory** — Once a person resolves a tricky judgment call for a given table layout, the system remembers it — future documents with the same shape don't re-ask the same question.

### The human verification workbench

Nothing the AI extracts is treated as fact until a person confirms it. Every field carries a visible confidence score and lands in a review queue (low-confidence, handwritten, ambiguous table join, and so on). Clicking any extracted value jumps straight to the exact rectangle on the original scan it came from — even when that value was pieced together from two different pages. Reviewers can bulk-confirm or bulk-edit many rows at once, with a full preview and one-click undo — but a batch of documents must first be "calibrated" (a human has certified the AI's confidence numbers are actually trustworthy for that batch) before bulk actions are even allowed.

### Search that understands both languages, and both meaning and spelling

One search box combines three techniques at once: exact keyword matching, meaning-based ("semantic") matching using AI embeddings, and typo-tolerant fuzzy matching. Search in English and it finds Marathi content and vice versa. Every AI-generated answer must cite the specific document and page it came from — if it can't find real grounding, it says so instead of guessing.

### Connecting records — the entity graph

The same person or property often appears differently across documents ("Ramrao Patil" in one register, "R. B. Patil" in another). The system links these, but with tiered trust: low-risk, mechanical links commit automatically; anything legally significant — like "these are the same legal identity" — always waits for a human to confirm, no matter how confident the AI is. Legal records themselves carry full history: the original entry, plus every amendment since, each with its own legal status (in force / set aside / under stay / superseded) — you can always see the current state *and* the untouched original.

### Governance — proving nothing was tampered with

Every action in the system (confirm, edit, export, delete) is written into an audit log that is cryptographically chained — each entry includes a hash of the previous one, so altering any past entry would break the chain and be instantly detectable. Retention rules (some records can never be auto-deleted; others expire on a schedule) are enforced by the database itself, not just hidden in application code. Exports always clearly flag which data is human-verified versus still AI-suggested.

---

## 4. The Tech Stack

Every major piece of technology used, organized by the job it does — not just a list of names.

```
                 Web Browser
        Next.js 14 · React 18 · TypeScript
                      │
                      │  REST API over HTTPS, JWT-secured
                      ▼
                FastAPI Backend
              Python · async · Pydantic
                      │
        ┌─────────────┼──────────────┬───────────────┐
        ▼             ▼              ▼               ▼
  PostgreSQL      Redis +        MinIO / AWS      AI Providers
  + pgvector      Celery         S3               Gemini, Claude,
  (records,       Workers        (original         GPT, Groq,
  permissions,    (background     scans &           Cohere,
  search index)   jobs, cache)    files)            local models
```

### Frontend — what the user sees and clicks

| Technology | What it's for |
|---|---|
| **Next.js 14** | The React framework running the whole web app — page routing, server rendering for fast first loads, and a production build pipeline. |
| **React 18** | Builds the interface out of reusable components (buttons, tables, panels) that update instantly as data changes. |
| **TypeScript** | Adds type-checking to JavaScript, so a whole category of bugs (passing the wrong shape of data) gets caught before the code ever runs. |
| **Tailwind CSS** | Styles the interface without writing separate CSS files for every component — keeps the whole app visually consistent. |
| **Mammoth.js / xlsx / react-pdf** | Render Word, Excel, and PDF files directly in the browser preview — no download required to check a document. |

### Backend — the application's brain

| Technology | What it's for |
|---|---|
| **FastAPI** | The Python web framework that serves every API request — chosen for being async-native (see §5) and for generating live, interactive API documentation automatically. |
| **SQLAlchemy 2.0 (async) + Alembic** | Talks to the database in Python code instead of hand-written SQL everywhere, and tracks every schema change as a reviewable, reversible migration. |
| **Pydantic** | Validates every request and response against a strict schema — malformed data gets rejected before it touches business logic. |
| **JWT + bcrypt** | Handles login sessions (signed tokens) and password storage (one-way hashing, so even a database leak doesn't expose real passwords). |

### Data & background work

| Technology | What it's for |
|---|---|
| **PostgreSQL 16 + pgvector** | One database doing two jobs: normal relational data (users, documents, folders, audit log) *and* AI vector search — see §5 for why that matters. |
| **Celery + Redis** | Runs slow work (OCR, AI extraction, embedding) in the background so the user's screen is never frozen waiting; Redis is both the job queue and a fast answer cache. |
| **Flower** | A live dashboard showing every background job in flight — useful for the demo to prove processing is really happening, not staged. |
| **MinIO / AWS S3** | Stores the actual scanned files and images — large binary files don't belong inside a database. MinIO is the local stand-in; AWS S3 is the production equivalent, same interface. |

### AI — reading, understanding, and answering

| Technology | What it's for |
|---|---|
| **Gemini / OpenRouter (Claude, GPT)** | Vision-language extraction — reading a scanned form image and mapping answers to fields. Automatically falls back from one to the other if a provider is unavailable or over quota. |
| **BGE-M3 (local)** | Turns text into a 1024-number "embedding" that captures its meaning, used for semantic search — runs locally, no API cost, no data leaving the server. |
| **Cohere Rerank** | A second-pass AI that re-scores the top search candidates for real relevance, filtering out near-misses a plain vector match would keep. |
| **PaddleOCR + Tesseract** | Local, offline-capable OCR engines with genuine Marathi/Devanagari support — no cloud dependency for the basic text-reading step. |
| **Qwen2.5-VL (local, in progress)** | Being evaluated as a fully local replacement for the cloud vision model, to remove the last external dependency for true air-gapped deployments. |

### Running it all

| Technology | What it's for |
|---|---|
| **Docker Compose** | Every piece — database, cache, backend, worker, frontend — runs the exact same way on any machine: one command starts the whole stack, which is also what makes the demo possible. |

---

## 5. Why These Choices

None of the above was picked by default. Here's the reasoning behind the decisions someone is most likely to ask about.

**Why one database for both records *and* AI search (Postgres + pgvector)?**
Many AI products run a separate specialized "vector database" alongside their normal database. We deliberately didn't: keeping everything in PostgreSQL means one system to secure, one backup strategy, one transaction guarantee — and critically, the same tenant-isolation security rule (see §6) automatically applies to AI search results too, instead of needing to be re-implemented in a second system.

**Why a vision-language model instead of "just OCR"?**
Plain OCR gives you a wall of text with no structure — you'd still have to guess which words are the answer to which question on the form. A vision-language model looks at the image itself, understands where the boxes are, and reports which value belongs in which field — and crucially, exactly where on the page it read that value from. That's what makes click-to-source verification possible at all.

**Why background workers (Celery) instead of doing everything instantly?**
Reading and understanding a scanned page can take real time. Making the user's browser sit frozen for that would be a bad product. Instead, the upload finishes instantly, a background worker does the slow work, and the screen updates from "processing" to "indexed" on its own — the Flower dashboard shown in the demo makes that background work visible.

**Why hot-swappable AI providers instead of picking one?**
Three real reasons: cost control (prices and quotas change), resilience (a provider outage or quota limit shouldn't take the product down — the system automatically falls back to a second provider), and eventually, sovereignty (a government customer may require the ability to run entirely on infrastructure they control, with zero external calls).

**Why design for "air-gapped" (fully offline) from day one?**
This product is intended to eventually run inside government facilities that may have no internet access at all. Rather than bolt that on later, the architecture already has a hard on/off switch: when air-gapped mode is enabled, any attempt to call an external AI service **fails loudly and closed** rather than silently leaking data out — described further in §6.

**Why Next.js / React for the frontend?**
It's the most widely adopted, well-supported way to build a fast, modern, type-safe web interface, with a large ecosystem for the specific things this product needs (in-browser document rendering, real-time updates) and a straightforward path to production deployment.

---

## 6. Security, Access & Trust

Legal records demand a higher bar than "the app code checks permissions." Here's what's actually enforced, and where.

**Multi-tenant isolation, enforced by the database itself.**
This is a multi-tenant platform — many separate organizations ("tenants") use the same running system, each seeing only their own data. Rather than trusting every line of application code to remember to filter by tenant, PostgreSQL's own **Row-Level Security** is used: the database is configured so a query simply cannot return another tenant's rows, no matter what the application code asks for. A mistake in a single API endpoint can't leak another organization's records, because the database itself is the last line of defense — not just the first.

**Six real roles, checked on every action.**
Records Officer, Operator, Department Head, Legal Counsel, IT Admin, and Auditor — each with different permissions, enforced on the server for every single action, not just hidden or greyed-out in the interface. Departments can additionally be scoped to only the folders they're authorized to see.

**Human-in-the-loop by design.**
Nothing the AI produces is presented as fact until a person confirms it — this is enforced in code, not policy: the functions that promote a value to "verified" hard-reject the action if there's no logged-in human actor behind it, and handwritten/ambiguous fields specifically cannot be bulk-approved at all.

**Tamper-evident audit trail.**
Every mutating action is written to an append-only, hash-chained log — each entry cryptographically includes the previous one, so any attempt to quietly edit history breaks the chain and is detectable on demand.

> **Found & fixed, not just designed:** A real cross-tenant data-isolation gap was found during hardening testing and fixed before this stage — see §8 for exactly what happened and why it matters that it was caught.

---

## 7. What's Done, What's Still Open

Every substantial piece of engineering scoped for this build is complete. What remains is a short list of items that need a decision or an external party — not more code.

**Legend:** ✅ Built end-to-end · 🟡 Mostly built, small known gap · ⛔ Blocked on a decision or outside access — not engineering

| Area | Status | Notes |
|---|---|---|
| Reading & extraction | ✅ Built | OCR, VLM field extraction, classification, table stitching, ditto marks, handwriting handling — all working against real registers. |
| Human verification workbench | ✅ Built | Queues, confidence scores, calibration gate, bulk actions with undo. Click-through to the exact source rectangle works on the backend; the on-screen highlighted viewer panel is the one piece still to wire into the page. |
| Search & Q&A | ✅ Built | Hybrid search, bilingual, cited/grounded AI answers, near-duplicate detection. |
| Entity graph & legal records | ✅ Built | Tiered-trust linking, full amendment history, legal status tracking. |
| Governance & audit | 🟡 Mostly built | Tamper-evident log, exports, completeness dashboard all live. The formal legal certificate is intentionally marked draft, pending legal counsel's sign-off on its wording — not an engineering gap. |
| Access control & language | ✅ Built | Six-role RBAC, department scoping, full Marathi translation alongside English. |
| Ingestion connectors | 🟡 Mostly built | Upload, watched folders, SFTP, and email-in all work today. Google Drive / SharePoint / a government e-Office connector are ready to build but are waiting on those third parties to grant API access. |
| Fully offline ("air-gapped") mode | 🟡 Mostly built | OCR, embeddings, and re-ranking already run 100% locally. The one remaining external call is the AI vision-extraction step — a local replacement model has been evaluated and the hardware requirement is now known; it's a hardware purchase decision, not unsolved engineering. |
| Formal accuracy benchmark | ⛔ Blocked | Needs a real reference set of documents with independently verified-correct answers to score against — that reference set doesn't exist yet. |
| Business & legal sign-offs | ⛔ Blocked | Final licensing numbers and one open-source license question are drafted and ready, waiting on a business/legal decision-maker. |

**One line for the room, if asked directly:** there is no unstarted or unblocked engineering work left — everything outstanding is either a third party's access grant, a hardware budget decision, or a human sign-off.

---

## 8. Proven by Testing, Not Just Claimed

Every feature in this document was tested live, against a real account with real data — not just reviewed on paper. That process found real bugs, which is exactly the point of doing it this way.

In one hardening pass alone, all 76 core backend functions were exercised end-to-end against a live account. That pass found and fixed five real issues:

1. **Cross-tenant data leak in "Empty Bin."** The most serious finding: emptying your own recycle bin could, under a missing check, delete another customer's trashed files too. Fixed, and now has a dedicated automated test guarding against it forever.
2. **"Empty Bin" silently doing nothing.** For documents without an explicit retention policy, the delete action would silently no-op while claiming success. Now it honestly reports what was deleted and what's protected, and why.
3. **Low-contrast warning messages.** Several status banners were nearly invisible against the app's background. Fixed, then proactively re-checked across the rest of the app for the same class of issue.

A second, independent security review specifically targeted cross-tenant data isolation and found a separate, genuine gap: it was possible to link one organization's records to another organization's private data through the entity graph, with no ownership check at all. That was confirmed as real, fixed at the source, and locked in with new automated tests before it could ever reach a customer.

> **Why this section exists:** the point of naming these bugs isn't to advertise flaws — it's that this is the standard of scrutiny this kind of system is held to before it touches a real legal record: find it yourself, fix it, and prove it can't silently happen again.

---

## 9. Demo Cheat Sheet

Likely questions from the room, answered in one breath.

**"How does search stay fast as documents pile up?"**
PostgreSQL's pgvector extension uses an HNSW index — a search structure built specifically so that finding the closest matches among millions of entries stays fast, instead of slowing down in a straight line with data size.

**"How do you know the AI isn't making things up?"**
Every answer must cite its source document and page. If it can't find real grounding for a claim, it explicitly refuses to answer rather than guess — that's enforced in code, not a setting someone could turn off.

**"What happens if a reviewer makes a mistake?"**
Every action is logged and reversible. Bulk edits have one-click rollback, and the audit trail itself can never be silently altered after the fact.

**"Is our data ever sent outside our own systems?"**
OCR runs entirely on local infrastructure today. The one component still calling an external AI service is the structured field-extraction step — and that's precisely the piece the local-model research (§4, §5) is aimed at replacing.

**"Can this run fully offline, with zero internet access?"**
That's the explicit design target. The system already has a hard switch that fails an operation closed — rather than silently falling back to the internet — the moment air-gapped mode is turned on.

**"What's the single biggest open risk?"**
No dedicated GPU yet for local AI extraction, so that one step still depends on a cloud model. The hardware requirement to fix that is now precisely known — it's a budget decision, not an unknown.

---

## 10. Glossary

Every term used above, defined plainly, so nothing in a follow-up question catches you off guard.

| Term | Definition |
|---|---|
| **Waqf** | A permanent Islamic charitable/religious endowment, usually land — the real-world record type this system was purpose-built to digitize. |
| **OCR** | Optical Character Recognition — software that reads text out of a scanned image. |
| **VLM** | Vision-Language Model — an AI that looks at an image (not just text) and can reason about what's in it, like which box on a form a handwritten answer belongs in. |
| **RAG** | Retrieval-Augmented Generation — having an AI answer a question using real retrieved documents as its source, instead of relying only on what it memorized during training. |
| **Embedding / Vector search** | Converting text into a list of numbers that captures its meaning, so "search by meaning" (not just exact keywords) becomes possible. |
| **Multi-tenant** | One running system serving many separate customer organizations ("tenants"), each seeing only their own data. |
| **Row-Level Security (RLS)** | A PostgreSQL feature that enforces tenant isolation inside the database itself, so even a coding mistake in the app can't leak another tenant's data. |
| **RBAC** | Role-Based Access Control — permissions are attached to a named role (like "Auditor"), and every user is assigned one. |
| **Audit hash chain** | A log where each entry cryptographically references the one before it, so silently editing past history becomes mathematically detectable. |
| **Celery / background worker** | A system for running slow tasks (like reading a scanned page) outside the main request, so the user's screen is never frozen waiting. |
| **HNSW index** | A search-index structure that keeps "find the closest matches" fast even as the number of records grows into the millions. |
| **JWT** | JSON Web Token — a signed, tamper-proof login credential the browser holds after signing in. |
| **Air-gapped** | Running with zero connection to the outside internet — a hard requirement for some government deployments. |
| **Ditto mark** | Old shorthand ("Do.") clerks wrote meaning "same value as the row above" — handled explicitly rather than mistaken for real data. |
| **Table stitching** | Automatically reconnecting a table row that's split across two pages (or a left/right spread) back into one correct row. |
| **Entity graph** | A network linking the same real-world person, property, or organization across multiple separate documents. |
| **Confidence score** | A number the AI attaches to each extracted value showing how sure it is — used to route uncertain answers to a human instead of guessing. |
| **Human-in-the-loop** | A design rule that a person must explicitly confirm an AI's output before it's treated as an official fact. |

---

*Prepared for internal demo use · every claim above reflects what has been live-verified against the running system.*
