# T31/T32 — regression corpus & accuracy baseline (starter, not A1)

**Status: genuine progress, not closure.** T25/T31/T32 remain blocked on **A1**
(no official human-verified reference corpus) and **D-4** (no agreed accuracy
tolerance number). This is a real, live-verified starting point built from
documents already in a real tenant — not synthetic, not invented — so the
next person to pick this up starts from evidence instead of nothing.

## What's in the corpus (2 real documents)

1. **`registration_file_juni_masjid,_hirpur,_murtizapur_akola.pdf`** —
   real handwritten/mixed Waqf registration file, 16 pages, matched to the
   `Waqf Institution Registration File` template (`single_page` layout,
   vertical table stitching). **Passing, 100% recall** on hand-verified
   ground truth (see `backend/scripts/accuracy_baseline.py`).
2. **`waqf_gazette_1973_spread_FIXED.pdf`** — real Maharashtra Government
   Gazette register, District Aurangabad, 15 Nov 1973, matched to the
   `Maharashtra State Wakf Gazette Register` template (`spread` layout,
   horizontal join across facing pages, columns 1-8 left / 9-19 right).
   **Known failing, documented, not silently ignored** — see below.

Ground truth for both was produced by rendering the real pages to PNG and
reading them directly (not by trusting the VLM's own output back).

## Two real bugs found and fixed while building this

1. **Null-bbox crash** (`vlm_extraction.py`, `table_stitch.py`): a field the
   VLM has no value for should omit its key entirely per the prompt, but the
   model doesn't always comply — it can return
   `{"bbox": [null, null, null, null], ...}` instead. The code only checked
   `bbox` was truthy; a 4-null list is a non-empty list, so it passed the
   check and then crashed on `float(None)` with an empty exception message.
   Fixed with a real `_valid_bbox()` check (all 4 coordinates must be actual
   numbers) at all 4 call sites.
2. **Raw newline inside a JSON string** (`vlm_extraction.py`,
   `_parse_vlm_response`): the model emitted a literal newline byte inside a
   cell value (`"Trees\nValuation Rs. 30."` with a real newline, not an
   escaped one) instead of escaping it. Python's `json.loads` rejects raw
   control characters in strict mode by default — one un-escaped newline in
   one cell lost every row on the page. Fixed with `strict=False`, which
   only relaxes that one rule and still requires valid JSON everywhere else.

Both fixes are real, narrow, and verified live against the actual malformed
responses that caused them (not hypothetical).

## Update 2026-09-01 — the parse-retry follow-up was built and it works

The left page (8 columns × 18 rows, dense, heavy ditto-mark usage) used to
produce **malformed JSON on 3 separate live attempts**, at a *different*
character position each time — a broken bracket structure, not a
control-character issue the two fixes above could touch. Model flakiness on
a wide/dense table, not a bug in this codebase.

Built the follow-up this note asked for: `_call_vlm_with_parse_retry()` in
`vlm_extraction.py`, same retry-on-unparseable pattern as
`table_stitch.adjudicate_structure`'s `ADJUDICATION_ATTEMPTS`. The one real
subtlety: retrying through the existing `_call_vlm_cached()` alone would do
nothing, since its cache key is a pure function of (file hash, page number,
prompt) — a naive retry would just replay the same cached bad response
forever. The fix bypasses the cache on retry attempts (a fresh sample from
the model, not the cached one) and — after discovering `record_vlm_response`
is write-once by design and silently no-ops on an existing key — added
`overwrite_vlm_response()` so a corrected response actually replaces the bad
one in the cache, instead of leaving it there for every future run to keep
retrying past. Unit-tested (`test_vlm_parse_retry.py`,
`test_extraction_archive_service.py`): malformed-then-good retry succeeds,
all-attempts-malformed degrades to 0 facts without crashing, and a
successful retry genuinely overwrites the cache (verified via a second,
independently-mocked VLM that would return different data if the cache
rewrite hadn't worked).

**Live-verified against the real gazette document** (`GAZETTE_DOC_ID`,
read-only — ran inside a DB transaction that was rolled back, never
committed, so the real tenant's data was never touched): attempt 1 on the
left page failed with the exact documented symptom
(`json.JSONDecodeError`, malformed structure), and the retry — a fresh,
uncached sample — parsed successfully on attempt 2. The specific bug this
note asked to fix (JSON-parse-level flakiness) is confirmed fixed.

**What's still open, and distinct from the parse fix above:** even with a
parseable response, this run's left/right join only recovered 2 real field
facts (`reviewed_by`) plus 2 `_join_mismatch` rows, not the full ~18-row
table. That's the row-matching/reconciliation layer (TS1's
`join_rows_horizontally`, T26's real-scan validation checklist below) —
getting valid JSON back doesn't by itself guarantee every row's serial
number matches cleanly between the two page halves. Still blocked on A1 for
a real second (and third, etc.) sample to know whether this run's row-match
rate is typical or an outlier — one confirmed real spread proves the
mechanism doesn't crash, not that it's accurate.

## Running it

```
docker compose exec backend python3 scripts/accuracy_baseline.py \
  --email <email> --password <password>
```

## T26 update 2026-09-01 — a second real spread document, and it corroborates checklist item #2

Found `Wardha.pdf` already in the real tenant (uploaded outside this
session, 14 pages, matched to the same gazette spread template) with
extraction already run. Read-only DB inspection (no re-run, no cost spent):
every one of its 5 measurable page-pairs (3-4, 5-6, 7-8, 9-10, 11-12) wrote
a `_join_mismatch` fact with the identical reason — `'sr_no' values on each
side disagree entirely, no shared value between the two fragments`. Pairs
1-2 and 13-14 produced neither a mismatch fact nor an error (silently
skipped — `if not left_rows or not right_rows: continue` — consistent with
non-tabular front/back matter, not a bug).

This is a **second independent real document showing the exact same
structural failure**: the role:`serial` field the code asks for on both
halves never actually matches between them. That's real corroborating
evidence for the real-scan validation checklist's item #2 in
`vlm_extraction.py::_extract_spread_facts` ("Is role:'serial' really
printed on BOTH halves of a real spread, or only once... if the latter,
the current 'ask serial on both sides' assumption is wrong"): with 2/2 real
spread documents showing a 100% left/right serial mismatch rate, "wrong
assumption" now looks like the likely answer, not just a documented
possibility. Registered as a second known-failing entry in
`accuracy_baseline.py` (`WARDHA_DOC_ID`) — not hand-verified against
ground truth (would need rendering+reading all 14 pages, out of scope for
this pass), just the observed real symptom, same honest-documentation
pattern as the first gazette.

**Still needs A1 to actually resolve**: fixing this would mean changing
the pairing strategy (e.g., matching by bbox vertical position only,
dropping the serial-match fast path entirely for this template) — a real
code change, but risky to make from 2 data points without knowing whether
either document's serial numbering is itself atypical (poor scan quality,
inconsistent handwriting) versus the pairing assumption being structurally
wrong for every real spread of this form type. Flagging, not fixing blind.

## T25 update 2026-09-01 — the two templates are now seeded, not live-only

Both templates existed only as hand-created rows in this dev DB (built
while assembling this corpus), so a fresh environment — a new dev DB, CI,
another deployment — would have neither, and the two documents above would
fail to classify entirely. Added migration `0045_seed_starter_templates`
(idempotent, `ON CONFLICT (form_type, era_label) DO NOTHING`, safe to run
against a DB where they already exist). Still not T25's real goal — a
template library seeded from an official, human-verified form catalogue,
which needs A1 — but it closes the "works on this one dev DB only" gap for
the two templates that do exist.

## What's needed to actually close T25/T31/T32

- **A1**: a real, official reference corpus with human-verified ground
  truth across a representative document sample — not 2 documents one
  person hand-checked in a session.
- **D-4**: someone needs to agree what accuracy is "good enough" — this
  report has no pass/fail bar, it just states recall.
- The gazette's left-page parse-retry fix (above) before that document can
  move from "documented known-failing" to "passing."
- Wiring `accuracy_baseline.py` (or its successor) into CI once real
  reference PDFs are committed to the repo — right now it depends on live
  data in a real tenant, which CI shouldn't depend on.
