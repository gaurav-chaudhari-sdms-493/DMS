"""T32 — accuracy baseline report against the T31 starter regression corpus.

Not the official A1 reference corpus (no human-verified ground truth
across a real sample set exists yet — that's still blocked on A1). This
is a small, honest starter: real documents already in a real tenant,
with ground truth hand-verified by directly reading the rendered page
images against the extracted Facts, not invented.

Usage (inside the backend container):
    python3 scripts/accuracy_baseline.py --email <email> --password <password>

Checks recovery, not exact-set equality: given the VLM's own run-to-run
variance (observed live this session — the same page re-extracted can
produce different text/row counts), asserting the full extracted set
matches exactly would be flaky by construction. Instead this checks
whether each hand-verified real value was recovered *somewhere* in the
document's Facts — a floor on recall, not a ceiling on precision.
"""
import argparse
import asyncio
import sys

import httpx

# Document 1 — registration_file_juni_masjid,_hirpur,_murtizapur_akola.pdf
# (Waqf Institution Registration File template, single_page layout).
# Ground truth hand-verified 2026-08-28 by rendering pages 10-11 to PNG
# and reading them directly (see conversation) against the item-6
# movable-property list and item-7 immovable-property table.
WAQF_DOC_ID = "d8e48897-d901-41e3-a613-8e240fa8c896"
WAQF_GROUND_TRUTH = [
    ("estimated_value", "800/-"),
    ("estimated_value", "1000/-"),
    ("estimated_value", "150/-"),
    ("estimated_value", "20/-"),
    ("property_description", "1 Bucket"),
    ("property_description", "1 Watch"),
]

# Document 2 — waqf_gazette_1973_spread_FIXED.pdf (Maharashtra State Wakf
# Gazette Register template, spread layout). STILL NOT a passing entry, but
# for a narrower reason now. The left-hand page's JSON-parse flakiness
# (malformed JSON on 3/3 attempts, 2026-08-28) is fixed as of 2026-09-01 —
# see T31_T32_regression_corpus_notes.md's "the parse-retry follow-up was
# built and it works" section: _call_vlm_with_parse_retry() recovers a
# malformed response by retrying with a fresh (uncached) sample, live-
# verified against this exact document. What's left is row-matching
# completeness (TS1/T26) — a parseable response doesn't guarantee every
# row's serial number joins cleanly between the two page halves, and that
# still needs more real samples (A1) to characterize as typical or not.
GAZETTE_DOC_ID = "139cd522-099e-4642-8199-10b6f6610694"
GAZETTE_KNOWN_ISSUE = (
    "JSON-parse flakiness on the left-hand page is fixed (parse-retry loop, "
    "2026-09-01, see T31_T32_regression_corpus_notes.md). Remaining gap: "
    "left/right row-matching completeness on this document's dense 18-row "
    "table is not yet consistently full-recall — needs more real spread "
    "samples (A1) to know if that's typical or this-document-specific."
)


# Document 3 — Wardha.pdf, same spread template, found already uploaded to
# the real tenant (2026-09-01, outside this session). Not hand-verified
# against ground truth (would need rendering+reading all 14 pages) — this
# is a structural known-failing entry, not a recall check: every one of
# its 5 measurable page-pairs disagreed entirely on serial number between
# left/right halves. See T31_T32_regression_corpus_notes.md's "a second
# real spread document, and it corroborates checklist item #2".
WARDHA_DOC_ID = "fc4263c7-4511-46c2-9590-dbb03458e8c7"
WARDHA_KNOWN_ISSUE = (
    "5/5 measurable page-pairs (3-4, 5-6, 7-8, 9-10, 11-12) failed to join — "
    "'sr_no' values disagree entirely between left and right halves on every "
    "pair, a 100% mismatch rate. Second real document showing this exact "
    "failure pattern (see WARDHA vs GAZETTE) — corroborates, doesn't yet fix, "
    "the checklist's item #2 concern that role:'serial' may not really be "
    "printed on both halves of a real spread."
)


async def check_document(base_url: str, token: str, document_id: str, ground_truth: list[tuple[str, str]]) -> dict:
    async with httpx.AsyncClient(base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0) as client:
        resp = await client.get("/api/v1/facts/queue", params={"category": "low_confidence", "limit": 500})
        resp.raise_for_status()
        facts = [f for f in resp.json()["facts"] if f["document_id"] == document_id]

    found, missing = [], []
    for field_name, expected_value in ground_truth:
        hit = any(
            f["field_name"] == field_name and str(f["value"].get("v", "")).strip() == expected_value
            for f in facts
        )
        (found if hit else missing).append((field_name, expected_value))

    return {"total_facts": len(facts), "found": found, "missing": missing}


async def main():
    parser = argparse.ArgumentParser(description="T32 accuracy baseline against the T31 starter corpus")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        resp = await client.post("/api/v1/auth/login", json={"email": args.email, "password": args.password})
        resp.raise_for_status()
        token = resp.json()["access_token"]

    print("=" * 70)
    print("T32 — Accuracy baseline (T31 starter corpus, NOT the official A1 corpus)")
    print("=" * 70)

    print("\n[1] Waqf Institution Registration File (single_page, vertical stitching)")
    result = await check_document(args.base_url, token, WAQF_DOC_ID, WAQF_GROUND_TRUTH)
    recall = len(result["found"]) / len(WAQF_GROUND_TRUTH) * 100
    print(f"    {result['total_facts']} total facts on the document")
    print(f"    Recall on hand-verified ground truth: {len(result['found'])}/{len(WAQF_GROUND_TRUTH)} ({recall:.0f}%)")
    for field_name, value in result["missing"]:
        print(f"    MISSING: {field_name} = {value!r}")

    print("\n[2] Maharashtra State Wakf Gazette Register — waqf_gazette_1973_spread_FIXED.pdf (spread, horizontal join)")
    print("    Status: KNOWN FAILING — row-matching incomplete, not a passing corpus entry")
    print(f"    {GAZETTE_KNOWN_ISSUE}")

    print("\n[3] Maharashtra State Wakf Gazette Register — Wardha.pdf (spread, horizontal join)")
    print("    Status: KNOWN FAILING — structural, not a passing corpus entry")
    print(f"    {WARDHA_KNOWN_ISSUE}")

    print("\n" + "=" * 70)
    print(f"Corpus size: 3 real documents (1 passing at {recall:.0f}% recall, 2 documented-failing)")
    print("This is a starter, not the A1 reference corpus — see T31_T32_regression_corpus_notes.md")
    print("=" * 70)

    return 0 if recall == 100 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
