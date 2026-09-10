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


async def resolve_duplicate_representatives(
    db: AsyncSession, tenant_id: UUID, doc_ids_by_rank: List[UUID], threshold: Optional[float] = None,
) -> Dict[UUID, UUID]:
    """Real bug found live (verification report, 2026-09-09): a chat
    answer's citation pointed at a different document than the one named
    in the user's own question -- the corpus has near-duplicate scans of
    the same underlying register (re-uploaded/rescanned copies), and
    search silently retrieved a chunk from the highest-SCORING duplicate,
    not necessarily the one the user meant. A same-session prompt-level
    mitigation (never assert a document identity beyond what the citation
    marker shows) papered over the symptom but left the actual retrieval
    behavior unchanged.

    This is the structural fix: given a small set of candidate document
    ids already in relevance-rank order (best first), groups any that are
    fuzzy-duplicates of each other (same T79 chunk_index=0 embedding
    comparison and threshold `find_fuzzy_duplicates` already uses at
    upload time — 0.92 by default, near-identical content only, never a
    merely-related document) and returns a mapping from every id to its
    cluster's REPRESENTATIVE: whichever document in that cluster ranked
    best. A caller then dedupes its per-document-id keys through this
    mapping, so a lower-ranked near-duplicate's chunks are silently
    skipped in favor of the higher-ranked duplicate's — the LLM (and the
    results list) never sees the confusing second copy at all, instead of
    seeing it and being told after the fact not to name it.

    Scoped intentionally to just the ids already in play for one query
    (typically under a dozen), not a background job or a persistent
    document-merge — matches this module's own "on-demand, never silently
    discard the underlying data" design (see find_fuzzy_duplicates'
    docstring): nothing here touches the documents or facts themselves,
    only which chunks one search response's results/citations draw from.
    """
    if len(doc_ids_by_rank) < 2:
        return {d: d for d in doc_ids_by_rank}

    if threshold is None:
        threshold = await get_float("duplicate_fuzzy_similarity_threshold", DEFAULT_FUZZY_SIMILARITY_THRESHOLD)

    ids_str = [str(d) for d in doc_ids_by_rank]
    res = await db.execute(
        text("""
            SELECT a.document_id AS doc_a, b.document_id AS doc_b,
                   1 - (a.embedding <=> b.embedding) AS similarity
            FROM doc_dg_chunks a
            JOIN doc_dg_chunks b
              ON a.chunk_index = 0 AND b.chunk_index = 0
             AND a.tenant_id = b.tenant_id
             AND a.document_id < b.document_id
            WHERE a.tenant_id = :tenant_id
              AND a.document_id = ANY(:doc_ids) AND b.document_id = ANY(:doc_ids)
        """),
        {"tenant_id": str(tenant_id), "doc_ids": ids_str},
    )

    adjacency: Dict[UUID, set] = {}
    for doc_a, doc_b, similarity in res.all():
        if similarity is None or float(similarity) < threshold:
            continue
        adjacency.setdefault(doc_a, set()).add(doc_b)
        adjacency.setdefault(doc_b, set()).add(doc_a)

    representative: Dict[UUID, UUID] = {}
    for doc_id in doc_ids_by_rank:
        if doc_id in representative:
            continue
        representative[doc_id] = doc_id
        for neighbor in adjacency.get(doc_id, ()):
            if neighbor not in representative:
                representative[neighbor] = doc_id
    return representative
