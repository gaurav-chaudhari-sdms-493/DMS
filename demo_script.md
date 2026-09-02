# Client Demo Script

A literal, read-aloud script for presenting the project — technical and
business framing woven together at each step. Weighted toward what's
new (the ingestion connectors, the security model in action) rather
than re-explaining product basics you already know cold.

Total run time: ~12-15 minutes if you do everything below; ~8 minutes
if you cut to the "Tight version" bookmarked at each section.

---

## Before you start

- [ ] `docker compose ps` — confirm all 9 containers say "Up"
- [ ] Log in as `biznesskd07@gmail.com` in one browser tab
- [ ] Have a file manager window pre-connected to the SFTP folder
- [ ] Have a terminal open, already `cd`'d into the project folder
- [ ] Pick 2-3 files you have **not** uploaded through any channel yet
      tonight, so nothing gets silently skipped as a duplicate on stage
- [ ] Second browser tab ready at the signup page, for the security beat

---

## 1. Open — one line, then move

> "I'm going to show you this live, not slides. Three things: how a
> document gets into the system without anyone having to think about
> it, how you find it again in seconds, and how it's kept separate from
> everyone else's data. Let's start with the part most systems get
> wrong."

*(Don't linger here — the opening line's job is to get you off the
title screen and into the product in under ten seconds.)*

---

## 2. Getting documents in — the part that's new

**Say:**
> "Most document systems assume one thing: that someone will remember
> to open the app and upload a file. In practice, that step gets
> skipped constantly — documents pile up 'to add later,' and later
> never comes. So we built this so a document gets in the moment it
> exists, no matter which system produced it or who's holding it."

### 2a. Auto-sync a real folder

**Do:** Drag a pre-picked file into `/home/stark/Stark Drive /` on
screen.

**Say:**
> "This is a folder on my computer I already use — nothing special
> about it. Watch."

*(while it processes, ~20-30 sec)*
> "No upload button, no login on this folder. DMS checks it
> automatically. In about twenty seconds this shows up fully indexed
> and searchable, same as a manual upload — because under the hood, it
> literally goes through the exact same pipeline."

**Do:** Switch to Drive, refresh, point at the file.

### 2b. Bring in a device that isn't this one

**Say:**
> "That folder only works because it's on this machine. What about a
> vendor, or another office, with no access to your server at all?"

**Do:** Click **+ New → Connect a device** → **Folder / SFTP** tab.

> "This is self-service — anyone on the team can open this panel and
> hand these details to an outside vendor themselves. No engineer has
> to issue credentials by hand."

**Do:** Switch to the pre-connected file manager window, drag a file
into the SFTP folder, then refresh Drive to show it land.

### 2c. Email — zero setup, zero training

**Say:**
> "And this is the one I think matters most, because it needs nothing —
> no client install, no server access, no training. Everyone already
> knows how to attach a file to an email."

**Do:** Click the **Email** tab in the same panel, point at the
address. Then, in the pre-positioned terminal:
```bash
cd "/home/stark/Work Space/DMS"
python3 send_demo_email.py "/path/to/a/fresh/file.pdf"
```
> "I just sent that as an email a second ago. Give it about ten
> seconds..."

**Do:** Refresh Drive, show it appear.

**Say, closing this section:**
> "Three completely different ways in — a folder, another server, an
> email — and every single one lands in the same place, searchable the
> same way, in about the same twenty seconds. Whatever already produces
> your documents today, this absorbs it without changing how your team
> works."

**Tight version:** if you're short on time, do only 2c (email) — it's
the fastest to set up on stage and the most visually convincing, since
the file is obviously arriving from "outside."

---

## 3. Finding it again — ask, don't search

**Say:**
> "Now the other half. Traditional systems make you remember the exact
> filename or folder. Here, you just ask."

**Do:** Type a natural-language question about one of the documents
you just added. Let the AI Summary Card render.

> "That's not a list of files to go open and read yourself — that's a
> synthesized answer, generated from the actual document content, with
> the exact source cited underneath. If you don't trust an AI's answer
> on faith, you don't have to — click through to the source page and
> verify it in one click."

**Do:** Click into a cited result, show the in-browser preview.

> "No download required to check a citation. That builds trust in the
> answer, which is the whole point of putting AI in front of your
> documents in the first place."

**Business framing (say if the audience is non-technical):**
> "The reason this matters commercially: your team stops spending time
> searching and starts spending time on the actual answer. That's the
> return on this, not a feature checkbox."

---

## 4. Multi-tenant security — the 30-second trust builder

**Say:**
> "One more thing, and this is the fastest way I can prove data
> isolation to you, rather than just claim it."

**Do:** Switch to the second browser tab, sign up a brand-new
organization live. Search for a term you know exists in the first
org's documents.

> "Zero results. Not because we filtered it in the application code —
> it's enforced at the database level, so there's no code path that
> could accidentally leak across organizations. If you're running this
> across departments or client accounts, this is the guarantee that
> matters."

---

## 5. One more trust signal — no vendor lock-in

**Do:** Open the `.env` config file (or just describe it if you'd
rather not show raw config on screen).

**Say:**
> "Every AI role here — the model that answers your questions, the
> embeddings, the reranker — is swappable with a one-line change. This
> isn't theoretical: during final testing last night, the AI provider
> we were using deprecated the exact model we had configured. Fixing
> production impact was a one-line change, not an emergency migration.
> You're never hostage to one AI vendor's pricing or uptime."

---

## Business positioning (reference — pull from as needed, don't read verbatim)

### The one-liner
> "Instead of your team searching through folders and filenames, they
> ask a question in plain language — and get back a direct answer,
> with the exact source document and page cited, in seconds. And
> documents get in on their own, however they already arrive."

### USP, ranked by what a client actually cares about
1. **Zero-effort intake** — folder, SFTP, or email, all converging on
   one pipeline; nothing requires a workflow change from your team.
2. **Ask, don't search** — grounded, cited answers, not a ranked list
   of files to open yourself.
3. **True multi-tenant isolation** — database-enforced, not an
   application check a bug could bypass.
4. **No AI vendor lock-in** — every AI role is configuration, not code.
5. **Trilingual out of the box** — English, Hindi, Marathi, one query
   surface.
6. **Transparent retrieval** — the system shows *how* it found an
   answer, not a black box.

### Traditional DMS vs. this system

| Traditional DMS | This system |
|---|---|
| One ingestion path, manual only | Folder, SFTP, or email — same pipeline, same guarantees |
| Find by browsing folders/filenames | Ask a question, get a cited answer |
| Search quality is fixed | Layered pipeline — each layer independently upgradeable |
| Usually single-tenant or weak isolation | Database-enforced multi-tenant isolation |
| Locked to one AI vendor (if any) | Swap providers via config, no rebuild |

### What it costs
> "At moderate volume — 100k documents, 50k searches a month — we're
> estimating roughly $250-450/month all-in, infra plus metered AI cost.
> Caching and candidate-filtering are built into the pipeline
> specifically to keep that from scaling linearly as usage grows."

---

## Anticipated Q&A

**"Is that email address real / does it use our actual mailbox?"**
> "For the demo we're running a local test mailbox so it doesn't depend
> on real internet delivery being fast in front of you. In your actual
> deployment it points at your real company mailbox — same mechanism,
> different address."

**"Can different people have different connector credentials?"**
> "Today it's one shared connector account per deployment. Per-user
> credentials with individual permissions is a natural next step, not
> a rebuild — happy to scope that with you directly."

**"Does it handle folders-inside-folders, or only flat files?"**
> "Full nested folder structures — drop a folder with subfolders in,
> and it recreates that exact structure as real folders in DMS, not
> flattened filenames." *(Demo live if you have an extra minute — drag
> a folder with one subfolder inside instead of a single file.)*

**"How is this different from just using ChatGPT on our files?"**
> "A general chatbot doesn't have persistent, tenant-isolated storage,
> doesn't cite the specific source page for every claim, and doesn't
> give you a search layer you can inspect and tune. This is retrieval
> with generation on top — not generation with search bolted on."

**"What happens if the AI gets something wrong?"**
> "It's instructed to answer only from retrieved excerpts, and every
> claim traces to a specific document and page — checkable in one
> click. It doesn't yet have a hard-refusal guarantee for ungrounded
> answers; that's on the roadmap, and I'd rather tell you that directly
> than have it surface as a surprise."

**"Can this run fully on our own infrastructure?"**
> "The core stack — database, storage, search — already runs fully
> self-hosted. The language model and reranking calls go to external
> AI APIs by default today, but because every AI role is
> provider-abstracted, pointing them at locally-hosted models is a
> configuration change, not a redesign."

**"What file types are supported?"**
> "PDF, Word, Excel, PowerPoint, plain text, CSV, RTF, images with OCR
> — and roughly thirty code/config formats added recently, since teams
> increasingly store more than office documents."

**"Is this production-ready, or a prototype?"**
> "Core platform — ingestion, hybrid search, multi-tenant security —
> is built and tested end to end, including live tonight. Some
> enterprise features — human-review workflows, tamper-evident audit
> trails, fine-grained role permissions — are near-term roadmap, not
> shipped yet. I'd rather say that directly than have you find the gap
> yourself later."

---

## Closing line

> "The short version: documents get in without anyone having to think
> about it, they get found by asking rather than browsing, and your
> data never touches anyone else's. That's the product."
