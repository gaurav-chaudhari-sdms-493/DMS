"""T79 — duplicate detection, the fuzzy half.

Hash-based exact-duplicate detection (document_service.upload_document)
was already built and blocks re-upload of a byte-identical file. This is
the other half the backlog calls out: "fuzzy matching for rescans" — a
document rescanned/re-photographed has a different SHA-256 but the same
content, so hash comparison can't catch it.

Reuses the embeddings already computed for every chunk at ingest (T05's
vector index) rather than a separate text-diff or perceptual-hash
pipeline: a rescan's OCR text is noisy (different line breaks, minor
misreads) but its *meaning* is the same, which is exactly what a
semantic embedding is robust to and a raw text diff isn't. Compares the
first chunk of each document — first chunk is representative content
without pulling every chunk's embedding into one expensive query.

On-demand, not a background job: "surface for operator resolution, do
not silently discard" (backlog). Nothing here blocks or auto-merges
anything — it just answers "does this document semantically resemble
something already in the tenant."
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.config_service import get_float

DEFAULT_FUZZY_SIMILARITY_THRESHOLD = 0.92


async def find_fuzzy_duplicates(
    db: AsyncSession, tenant_id: UUID, document_id: UUID, threshold: Optional[float] = None, limit: int = 10,
) -> List[Dict[str, Any]]:
    # T03 — sourced from sys_dg_config (migration 0041) when the caller
    # doesn't explicitly override it; falls back to this module's own
    # constant if the config row is ever missing.
    if threshold is None:
        threshold = await get_float("duplicate_fuzzy_similarity_threshold", DEFAULT_FUZZY_SIMILARITY_THRESHOLD)

    target_res = await db.execute(
        text("""
            SELECT c.embedding FROM doc_dg_chunks c
            WHERE c.document_id = :document_id AND c.tenant_id = :tenant_id
            ORDER BY c.chunk_index ASC LIMIT 1
        """),
        {"document_id": str(document_id), "tenant_id": str(tenant_id)},
    )
    target_row = target_res.first()
    if not target_row:
        return []
    target_embedding = target_row[0]

    res = await db.execute(
        text("""
            SELECT DISTINCT ON (d.id)
                d.id AS document_id, d.title,
                1 - (c.embedding <=> CAST(:target_embedding AS vector)) AS similarity
            FROM doc_dg_chunks c
            JOIN doc_dg_documents d ON d.id = c.document_id
            WHERE c.tenant_id = :tenant_id
              AND c.chunk_index = 0
              AND d.id != :document_id
              AND d.is_trashed = false
            ORDER BY d.id, c.embedding <=> CAST(:target_embedding AS vector)
        """),
        {"target_embedding": str(target_embedding), "tenant_id": str(tenant_id), "document_id": str(document_id)},
    )
    rows = res.all()

    candidates = [
        {"document_id": str(doc_id), "title": title, "similarity": round(float(sim), 4)}
        for doc_id, title, sim in rows
        if sim >= threshold
    ]
    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    return candidates[:limit]
