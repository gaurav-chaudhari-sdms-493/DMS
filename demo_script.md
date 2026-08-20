# VeritasDocs — Client Demo Script & Positioning

Prepared: 20-Aug-2026 · For: client demonstration, 21-Aug-2026

This is the business-facing companion to `project_study.md`. Use this
for the pitch, positioning, and anticipated Q&A. Use the study doc if
the conversation goes deep technical.

---

## 1. The One-Liner

> "Instead of your team searching through folders and filenames, they
> ask a question in plain language — and get back a direct answer,
> with the exact source document and page cited, in seconds."

---

## 2. The 60-Second Pitch

Most organizations don't have a search problem because they lack
documents — they have one because they have *too many*, scattered
across drives, and nobody can find the right one fast enough. Keyword
search only works if you remember the exact word someone used in a file
from three years ago.

This platform ingests documents from wherever your team already puts
them — manual upload, a watched network folder, or SFTP — and makes
every one of them instantly askable. Not just searchable: *askable*.
Your team types a question the way they'd ask a colleague, and gets a
grounded answer with citations, not a list of maybe-relevant links.

It's built multi-tenant from day one, so if you're running this across
departments or client accounts, each one's data is isolated at the
database level — not just hidden behind a login screen.

---

## 3. Our Unique Selling Points (USP)

1. **Ask, don't search.** Natural-language questions get synthesized,
   cited answers — not a ranked list of files to open and read yourself.
2. **Multi-channel ingestion, one pipeline.** Drag-and-drop, a watched
   folder, or SFTP — documents get in the way your existing workflow
   already works, and every channel behaves identically once ingested
   (same dedup, same security, same search quality).
3. **True multi-tenant isolation.** Database-enforced row-level
   security, not an application-layer permission check that a bug could
   bypass.
4. **Vendor-independent AI.** Every AI role — the language model, the
   embeddings, the reranker, the OCR engine — is swappable via
   configuration. You are never locked into one AI vendor's pricing or
   uptime.
5. **Trilingual out of the box.** Query in English, Hindi, or Marathi —
   the system searches across all three, so language isn't a barrier to
   finding a document.
6. **Transparent retrieval.** The system tells you *how* it found an
   answer (semantic match, keyword match, or a hybrid of both) — not a
   black box.
7. **Cost-engineered, not just feature-engineered.** Caching and
   candidate-filtering are built into the pipeline specifically to keep
   AI API costs from scaling linearly with usage.

---

## 4. Traditional Document Management vs. This System

| Traditional DMS | This System |
|---|---|
| Find documents by browsing folders or matching filenames/keywords | Ask a question, get a synthesized answer with source citations |
| One search experience, one language | Trilingual query understanding built in |
| A search hit is a black box — you don't know why it matched | Every result reports how it was found and how confident the match is |
| Usually single-tenant, or multi-tenant with weak isolation | Multi-tenant with database-enforced isolation |
| Locked into whichever AI vendor (if any) the platform shipped with | Swap AI providers via configuration — no rebuild, no vendor lock-in |
| One ingestion path, typically manual only | Three ingestion channels today (manual, watched folder, SFTP), same pipeline, same guarantees |
| Search quality is fixed | Layered retrieval pipeline — each layer (cache, hybrid search, reranking, generation) can be independently upgraded as better models emerge |

---

## 5. Why We Stand Out From Other Document Search / DMS Products

- **We're not a search box bolted onto a file drive.** The retrieval
  pipeline (hybrid search → reranking → grounded generation) is the
  product, not a feature checkbox — most competitors offer either
  keyword search *or* a thin AI chat wrapper, not both engineered
  together with citation-level grounding.
- **We don't hide the mechanism.** Competitors that use AI search
  typically present a single opaque "smart search" box. We show which
  retrieval strategy produced the answer and let that inform trust.
- **We built for multi-tenant from the schema up**, not retrofitted
  — this matters immediately if you're serving multiple business units,
  departments, or clients from one deployment.
- **No AI vendor hostage situation.** This was proven, not just
  claimed: during final testing, an AI provider deprecated the specific
  model we were using — production impact was a one-line config change,
  not an emergency migration.
- **Ingestion meets you where you are.** Most DMS platforms assume
  manual upload as the only path in. We support automated pickup from
  a watched folder or SFTP server today, so document intake can be
  automated from existing infrastructure rather than requiring a
  behavior change from every user.

---

## 6. Recommended Live Demo Flow

Follow `docs/DEMO_PRESENTATION_GUIDE.md` for the detailed script. High-level flow:

1. **Login** — multi-tenant workspace, clean dashboard.
2. **Upload** — drag a file in, show it go from `processing` to
   `indexed` live (Flower dashboard as a nice technical beat if the
   audience is technical).
3. **Ask a question** — the headline moment. Type a natural-language
   question, get a synthesized answer with citations and a working
   source download link.
4. **Preview a result in-browser** — no download required to verify a
   citation.
5. **Register a second organization live** — search for the first
   org's content, get zero results. This is the most convincing security
   demonstration you can give in 30 seconds.
6. **Show the config file** — point at the AI provider setting, explain
   it's a one-line swap. Mention the real incident (§5) if it lands well
   with a technical audience.

*(Watched-folder / SFTP automated ingestion can be shown as a bonus beat
in step 2 if time allows — pre-stage the file a few seconds before you
get there so you're not waiting on a live poll cycle.)*

---

## 7. Anticipated Questions & Recommended Answers

**"How is this different from just using ChatGPT on our files?"**
> A general chatbot doesn't have persistent, tenant-isolated storage
> of your documents, doesn't cite the specific source page for every
> claim, and doesn't give you a search layer you can inspect and tune.
> This is a retrieval system with generation on top — not generation
> with search bolted on. The citation is the product, not a nice-to-have.

**"What happens if the AI gets something wrong?"**
> The generation step is instructed to answer *only* from retrieved
> excerpts, and every claim is traceable to a specific document and
> page — so a wrong or unsupported answer is checkable in one click,
> not something you have to take on faith. [Note: the system does not
> yet have a hard-refusal guarantee for ungrounded answers — that's on
> the roadmap. Be honest if pressed on this specifically.]

**"Can this run entirely on our own infrastructure, with no data
leaving our network?"**
> The core stack (database, storage, search) already runs fully
> self-hosted. Today, the language model and reranking calls go to
> external AI APIs by default — but because every AI role is
> provider-abstracted, pointing them at locally-hosted models instead
> is a configuration change, not a redesign. A fully air-gapped profile
> is on the roadmap, not yet shipped.

**"How do you handle multiple clients/departments on one deployment?"**
> Database-level row-level security, not just application logic —
> we can show this live: a fresh account genuinely cannot see another
> tenant's documents, verified at the database layer.

**"What does this cost to run?"**
> It scales with usage rather than a flat license fee — infra cost
> plus metered AI cost. At moderate volume (100k documents, 50k
> searches/month) we're estimating roughly $250–450/month all-in,
> with caching and candidate-filtering specifically built in to keep
> that from scaling linearly as usage grows. [Full breakdown available
> in the costing document if asked for specifics.]

**"What file types do you support?"**
> PDF, Word, Excel, PowerPoint, plain text/CSV/RTF, and images —
> including scanned documents via OCR.

**"How do documents get into the system — does someone have to upload
everything manually?"**
> Three ways today: manual drag-and-drop, an automated watched folder,
> or SFTP — all converging on the same pipeline, so ingestion can be
> automated from whatever system already produces these documents,
> not just a manual habit you have to build.

**"Is this production-ready today, or a prototype?"**
> The core platform — ingestion, hybrid search, multi-tenant security
> — is built and tested end-to-end. Some enterprise-grade features
> (human-review workflows for extracted data, tamper-evident audit
> trails, fine-grained role permissions) are on the near-term roadmap,
> not yet shipped. We'd rather tell you that directly than have it
> surface as a surprise later. [Have this answer ready — it builds more
> trust than pretending everything is finished, and a technical
> evaluator will likely find the gaps anyway.]

**"What languages does search support?"**
> English, Hindi, and Marathi today, with the architecture built to
> extend to more — a query in one language can retrieve a document
> written in another.

**"Can we customize / white-label this?"**
> Frame as: the platform is modular by design (provider abstraction,
> configurable ingestion channels) — customization scope is a
> conversation for the next meeting, not something to commit to
> specifics on live.

---

## 8. One Honest Note for the Presenter

Don't oversell items from the "not yet built" list in `project_study.md`
§9 if asked directly — the recommended answers above already thread
that needle. A confident, specific "that's on our near-term roadmap,
here's what's solid today" lands far better with a technical evaluator
than an evasive answer, and it's consistent with how this system itself
is designed to work: don't answer past what's actually grounded.
