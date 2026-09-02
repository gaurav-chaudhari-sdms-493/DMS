#!/usr/bin/env python3
"""TS8 — OCR engine comparison / bake-off harness.

Runs pdfplumber's native text layer, Tesseract, and PaddleOCR against
the same rendered page(s) of an already-uploaded document and prints a
structured, ground-truth-free comparison (see
app/services/ocr_bakeoff_service.py for what's actually being measured
and why). Meant to inform AI_OCR_PROVIDER defaults per document
type/language — the recommendation printed here is decision support
only, never applied automatically.

Usage:
    python3 scripts/ocr_bakeoff.py --document-id <uuid> [--pages 1,4,11] [--json]
"""
import argparse
import asyncio
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import UUID

from app.database import AsyncSessionLocal
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.services.ocr_bakeoff_service import run_bakeoff_on_page
from app.services.storage_service import download_file


async def run_bakeoff(document_id: UUID, page_numbers, as_json: bool) -> None:
    import pdfplumber

    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, document_id)
        if not doc:
            print(f"No document {document_id}")
            return
        version = await db.get(DocumentVersion, doc.current_version_id) if doc.current_version_id else None
        if not version:
            print(f"Document {document_id} has no current version")
            return

        print(f"Downloading '{doc.title}' ({document_id})...")
        file_bytes = await download_file(version.s3_path)

    all_results = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        target_pages = page_numbers or list(range(1, len(pdf.pages) + 1))
        for pn in target_pages:
            if pn < 1 or pn > len(pdf.pages):
                print(f"  page {pn}: out of range, skipping")
                continue
            page = pdf.pages[pn - 1]
            print(f"Running bake-off on page {pn}/{len(pdf.pages)}...")
            result = run_bakeoff_on_page(page)
            all_results.append(result)

            if not as_json:
                rec = result["recommendation"]
                print(f"  page {result['page_number']}: recommend '{rec['engine']}' ({rec['reason']})")
                for engine, r in result["results"].items():
                    ts, bs = r["text_score"], r["bbox_score"]
                    print(
                        f"    {engine:18s} chars={ts['char_count']:5d}  "
                        f"rows={ts['row_like_line_count']:3d}  "
                        f"devanagari={ts['devanagari_char_ratio']:.0%}  "
                        f"degenerate={ts['is_degenerate_table']!s:5s}  "
                        f"bbox({bs['granularity']})={bs['bbox_coverage']:.0%} of {bs['unit_count']}"
                    )

    if as_json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    else:
        engine_wins = {}
        for r in all_results:
            eng = r["recommendation"]["engine"]
            if eng:
                engine_wins[eng] = engine_wins.get(eng, 0) + 1
        print(f"\nAcross {len(all_results)} page(s), recommended engine by page: {engine_wins}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--document-id", required=True, type=UUID)
    parser.add_argument("--pages", type=str, default=None, help="comma-separated 1-indexed page numbers, default all")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    page_numbers = [int(p) for p in args.pages.split(",")] if args.pages else None
    asyncio.run(run_bakeoff(args.document_id, page_numbers, args.as_json))
