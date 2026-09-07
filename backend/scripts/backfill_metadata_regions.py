#!/usr/bin/env python3
"""T05 — backfill doc_dg_metadata_item_regions for metadata items written
before source-location attribution existed.

Doesn't need to re-download or re-OCR the original file: doc_dg_chunks
already persisted each page's word_regions in chunk_metadata at ingest
time (see chunker.py/worker.py), so this reconstructs the same per-page
{"page_number", "text", "words"} structure source_location_service expects
directly from existing chunk rows, grouping by page_number (a page can
span several chunks; their `content` is concatenated for the substring
pre-check, and word_regions is identical across chunks from the same page
so the first one found is used).

Only touches metadata items that have zero regions today -- safe to
re-run, and safe to run alongside new ingestion (which now writes its own
region at insert time and would already have one here).

Usage:
    docker compose exec backend python3 scripts/backfill_metadata_regions.py [--dry-run]
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.metadata_item import MetadataItem
from app.models.metadata_item_region import MetadataItemRegion
from app.services.source_location_service import locate_value_in_pages


async def _pages_from_chunks(db, version_id):
    res = await db.execute(
        select(Chunk).where(Chunk.version_id == version_id).order_by(Chunk.page_number, Chunk.chunk_index)
    )
    chunks = res.scalars().all()
    pages_by_number = {}
    for c in chunks:
        pn = c.page_number
        if pn is None:
            continue
        if pn not in pages_by_number:
            words = (c.chunk_metadata or {}).get("word_regions") or []
            pages_by_number[pn] = {"page_number": pn, "text": "", "words": words}
        pages_by_number[pn]["text"] += " " + (c.content or "")
    return list(pages_by_number.values())


async def backfill(dry_run: bool) -> None:
    attempted = 0
    located = 0
    skipped_no_chunks = 0

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(MetadataItem.id, MetadataItem.document_id, MetadataItem.value)
            .outerjoin(MetadataItemRegion, MetadataItemRegion.metadata_item_id == MetadataItem.id)
            .where(MetadataItemRegion.id.is_(None))
        )
        rows = res.all()
        print(f"{len(rows)} metadata item(s) with no region yet.")

        pages_cache = {}  # document_id -> pages list, most docs have several metadata items each
        for item_id, document_id, raw_value in rows:
            attempted += 1
            value = raw_value.get("v") if isinstance(raw_value, dict) else raw_value
            if not isinstance(value, str):
                continue

            if document_id not in pages_cache:
                doc = await db.get(Document, document_id)
                if not doc or not doc.current_version_id:
                    pages_cache[document_id] = None
                else:
                    pages_cache[document_id] = await _pages_from_chunks(db, doc.current_version_id)

            pages = pages_cache[document_id]
            if not pages:
                skipped_no_chunks += 1
                continue

            location = locate_value_in_pages(value, pages)
            if not location:
                continue

            located += 1
            if not dry_run:
                doc = await db.get(Document, document_id)
                db.add(MetadataItemRegion(
                    tenant_id=doc.tenant_id,
                    metadata_item_id=item_id,
                    page_number=location["page_number"],
                    x0=location["x0"], y0=location["y0"], x1=location["x1"], y1=location["y1"],
                ))

        if not dry_run:
            await db.commit()

    print(
        f"Attempted {attempted}, located {located} region(s)"
        f"{' (dry run, nothing written)' if dry_run else ' (written)'}, "
        f"{skipped_no_chunks} skipped (document has no stored chunks to attribute against)."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Report what would be written without writing it.")
    args = parser.parse_args()
    asyncio.run(backfill(args.dry_run))
