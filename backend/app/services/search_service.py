import time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.schemas.search import SearchResponse, SearchResult
from app.services.cache_service import get_cached_search, cache_search_result, generate_cache_key
from app.services.audit_service import log_action
from app.services.storage_service import generate_presigned_url
from app.ai.factory import get_embed_provider, get_rerank_provider, get_llm_provider
from app.ai.base import Message
from app.models.metadata_item import MetadataItem

async def search(
    query: str,
    tenant_id: UUID,
    user_id: UUID,
    limit: int,
    filters: dict | None,
    db: AsyncSession,
    ip_address: str,
) -> SearchResponse:
    
    start_time = time.time()
    
    # Enforce AI Input Guardrails
    from app.services.guardrail_service import validate_input_query, validate_output_summary
    is_safe, error_msg, scrubbed_query = validate_input_query(query)
    if not is_safe:
        took_ms = int((time.time() - start_time) * 1000)
        return SearchResponse(
            query=query,
            ai_summary=f"Safety Block: {error_msg}",
            results=[],
            cached=False,
            took_ms=took_ms
        )
    
    query = scrubbed_query
    
    cache_key = generate_cache_key(str(tenant_id), query, filters)
    cached = await get_cached_search(cache_key)
    if cached:
        return cached
        
    # 2. Embed
    embed_provider = get_embed_provider()
    embeddings = await embed_provider.embed([query])
    q_emb = embeddings[0]
    q_emb_str = "[" + ",".join(str(f) for f in q_emb) + "]"
    
    # Build filter clauses dynamically for hybrid search
    filter_clauses = []
    params = {
        "query": query,
        "tenant_id": tenant_id,
    }
    
    if filters:
        for idx, (k, v) in enumerate(filters.items()):
            if k == "doc_type":
                filter_clauses.append(f"AND d.doc_type = :filter_{idx}")
                params[f"filter_{idx}"] = v
            else:
                # Treat as custom metadata item filter
                filter_clauses.append(f"""
                    AND EXISTS (
                        SELECT 1 FROM metadata m 
                        WHERE m.document_id = d.id 
                          AND m.key = :filter_key_{idx} 
                          AND (
                            m.value->>'v' = :filter_val_{idx} 
                            OR m.value->> :filter_key_{idx} = :filter_val_{idx}
                            OR m.value::text = :filter_val_{idx}
                            OR m.value::text LIKE :filter_like_val_{idx}
                          )
                    )
                """)
                params[f"filter_key_{idx}"] = k
                params[f"filter_val_{idx}"] = str(v)
                params[f"filter_like_val_{idx}"] = f'%"{v}"%'
                
    filter_str = "\n".join(filter_clauses)
    
    # 3. Vector search (pgvector <=> operator)
    vec_sql = text(f"""
        SELECT c.chunk_id as id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               1 - (c.embedding <=> CAST(:query_embedding AS vector)) as vector_score
        FROM chunks c 
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN document_versions v ON c.version_id = v.id
        WHERE d.tenant_id = :tenant_id AND d.status = 'indexed' {filter_str}
        ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
        LIMIT 20
    """)
    
    vec_res = await db.execute(vec_sql, {**params, "query_embedding": q_emb_str})
    vec_rows = vec_res.fetchall()
    
    # 4. Keyword search (dynamic tsvector full-text search)
    kw_sql = text(f"""
        SELECT c.chunk_id as id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               ts_rank(to_tsvector('english', c.content), q) as keyword_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN document_versions v ON c.version_id = v.id,
        plainto_tsquery('english', :query) q
        WHERE to_tsvector('english', c.content) @@ q AND d.tenant_id = :tenant_id AND d.status = 'indexed' {filter_str}
        ORDER BY keyword_score DESC
        LIMIT 20
    """)
    
    kw_res = await db.execute(kw_sql, params)
    kw_rows = kw_res.fetchall()
    
    # 5. RRF Merge (Reciprocal Rank Fusion)
    rrf_scores = {}
    docs_map = {}
    k = 60
    
    for rank, row in enumerate(vec_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = 1.0 / (k + rank + 1)
        
    for rank, row in enumerate(kw_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank + 1)
        
    merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:20]
    
    if not merged:
        took_ms = int((time.time() - start_time) * 1000)
        resp = SearchResponse(
            query=query,
            ai_summary="No matching documents were found in the database.",
            results=[],
            cached=False,
            took_ms=took_ms
        )
        await log_action(db, user_id, tenant_id, "search.query", details={"query": query, "result_count": 0, "took_ms": took_ms}, ip_address=ip_address)
        return resp
        
    # 6. Rerank
    reranker = get_rerank_provider()
    doc_texts = [docs_map[cid].content for cid, _ in merged]
    reranked = await reranker.rerank(query, doc_texts, top_n=limit)
    
    final_results = []
    snippets_for_llm = []
    doc_ids_for_metadata = []
    
    for rank_res in reranked:
        idx = rank_res.index
        cid, _ = merged[idx]
        row = docs_map[cid]
        doc_ids_for_metadata.append(row.doc_id)
        
    # Query metadata for all returned documents
    meta_map = {}
    if doc_ids_for_metadata:
        stmt = select(MetadataItem).where(MetadataItem.document_id.in_(doc_ids_for_metadata))
        meta_res = await db.execute(stmt)
        for m in meta_res.scalars().all():
            doc_id = m.document_id
            if doc_id not in meta_map:
                meta_map[doc_id] = {}
            val = m.value
            if isinstance(val, dict) and "v" in val:
                val = val["v"]
            meta_map[doc_id][m.key] = val
            
    for rank_res in reranked:
        idx = rank_res.index
        cid, _ = merged[idx]
        row = docs_map[cid]
        
        s3_path = row.s3_path
        url = await generate_presigned_url(s3_path) if s3_path else ""
        
        final_results.append(SearchResult(
            document_id=row.doc_id,
            document_name=row.title,
            download_url=url,
            page_number=row.page_number,
            snippet=row.content,
            score=rank_res.score,
            metadata=meta_map.get(row.doc_id, {})
        ))
        snippets_for_llm.append(f"Document: {row.title}\nExcerpt: {row.content}")
        
    # 7. Summary
    llm = get_llm_provider()
    sys_msg = (
        "You are a helpful document assistant. Answer the user's question clearly and concisely using only the provided document excerpts. "
        "Note that 'marks' or 'grades' can refer to any scores, grades, numbers, ratios, or percentages mentioned in the context. "
        "If the excerpts do not contain any relevant information to answer the question, state that the information was not found."
    )
    user_msg = f"Question: {query}\n\nExcerpts:\n" + "\n---\n".join(snippets_for_llm)
    summary = await llm.complete([
        Message(role="system", content=sys_msg),
        Message(role="user", content=user_msg)
    ])
    
    # Enforce AI Output Guardrails
    summary = validate_output_summary(summary)
    
    took_ms = int((time.time() - start_time) * 1000)
    
    resp = SearchResponse(
        query=query,
        ai_summary=summary,
        results=final_results,
        cached=False,
        took_ms=took_ms
    )
    
    # Audit log & Cache
    await log_action(db, user_id, tenant_id, "search.query", details={"query": query, "result_count": len(final_results), "took_ms": took_ms}, ip_address=ip_address)
    await cache_search_result(cache_key, resp)
    
    return resp
