import time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas.search import SearchResponse, SearchResult
from app.services.cache_service import get_cached_search, cache_search_result, generate_cache_key
from app.services.audit_service import log_action
from app.services.storage_service import generate_presigned_url
from app.ai.factory import get_embed_provider, get_rerank_provider, get_llm_provider
from app.ai.base import Message

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
    
    cache_key = generate_cache_key(str(tenant_id), query, filters)
    cached = await get_cached_search(cache_key)
    if cached:
        return cached
        
    # 2. Embed
    embed_provider = get_embed_provider()
    embeddings = await embed_provider.embed([query])
    q_emb = embeddings[0]
    q_emb_str = f"[{','.join(str(x) for x in q_emb)}]"
    
    # 3. Vector search
    vec_sql = text("""
        SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               1 - (c.embedding <=> CAST(:query_embedding AS vector)) as vector_score
        FROM chunks c 
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN document_versions v ON v.document_id = d.id
        WHERE d.tenant_id = :tenant_id AND d.status = 'indexed'
        ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
        LIMIT 20
    """)
    
    vec_res = await db.execute(vec_sql, {"query_embedding": q_emb_str, "tenant_id": str(tenant_id)})
    vec_rows = vec_res.fetchall()
    
    # 4. Keyword search
    kw_sql = text("""
        SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               ts_rank(c.content_tsv, q) as keyword_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN document_versions v ON v.document_id = d.id,
        plainto_tsquery('english', :query) q
        WHERE c.content_tsv @@ q AND d.tenant_id = :tenant_id AND d.status = 'indexed'
        ORDER BY keyword_score DESC
        LIMIT 20
    """)
    
    kw_res = await db.execute(kw_sql, {"query": query, "tenant_id": str(tenant_id)})
    kw_rows = kw_res.fetchall()
    
    # 5. RRF Merge
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
            ai_summary="The answer was not found in the available documents.",
            results=[],
            cached=False,
            took_ms=took_ms
        )
        await log_action(db, user_id, tenant_id, "search.query", details={"query": query, "result_count": 0, "took_ms": took_ms}, ip_address=ip_address)
        return resp

    reranker = get_rerank_provider()
    doc_texts = [docs_map[cid].content for cid, _ in merged]
    reranked = await reranker.rerank(query, doc_texts, top_n=limit)
    
    final_results = []
    snippets_for_llm = []
    
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
            metadata={}
        ))
        snippets_for_llm.append(f"Document: {row.title}\nExcerpt: {row.content}")
        
    # 7. Summary
    llm = get_llm_provider()
    sys_msg = "You are a document assistant. Answer the user's question using ONLY the provided document excerpts. If the answer is not present in the excerpts, say: 'The answer was not found in the available documents.' Do not add any information not present in the excerpts."
    user_msg = f"Question: {query}\n\nExcerpts:\n" + "\n---\n".join(snippets_for_llm)
    summary = await llm.complete([
        Message(role="system", content=sys_msg),
        Message(role="user", content=user_msg)
    ])
    
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
