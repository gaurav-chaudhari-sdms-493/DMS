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

## What's still genuinely broken — the gazette's left-hand page

The left page (8 columns × 18 rows, dense, heavy ditto-mark usage) produced
**malformed JSON on 3 separate live attempts**, at a *different* character
position each time — a broken bracket structure, not a control-character
issue the two fixes above could touch. This is model flakiness on a
wide/dense table, most likely related to response length/complexity, not a
bug in this codebase. The right-hand page (11 columns) parses reliably now.

**Real follow-up needed, not done here** (ran out of budget to chase this
further in one session): either shrink the per-call row batch for wide
tables, or add a parse-retry loop on `_extract_spread_facts`'s per-page-pair
VLM calls — the same pattern `table_stitch.adjudicate_structure`'s
`ADJUDICATION_ATTEMPTS` already uses for exactly this class of flakiness.

## Running it

```
docker compose exec backend python3 scripts/accuracy_baseline.py \
  --email <email> --password <password>
```

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
