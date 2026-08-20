import time
import re
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.schemas.search import SearchResponse, SearchResult
from app.services.cache_service import get_cached_search, cache_search_result, generate_cache_key
from app.services.audit_service import log_action
from app.services.storage_service import generate_presigned_url
import json
from app.ai.factory import get_embed_provider, get_rerank_provider, get_llm_provider
from app.ai.base import Message, RankedResult
from app.models.metadata_item import MetadataItem

logger = logging.getLogger(__name__)


def _make_snippet(content: str, max_chars: int = 400) -> str:
    """Truncate result snippet around boundary to keep payload light."""
    if not content or len(content) <= max_chars:
        return content or ""
    return content[:max_chars].rsplit(" ", 1)[0] + "…"


async def _expand_trilingual_query(query: str) -> dict:
    """Expand user query into normalized English, Hindi, and Marathi search variants."""
    try:
        llm = get_llm_provider()
        sys_msg = (
            "You are a multilingual AI query normalization assistant for enterprise document search in India.\n"
            "Analyze the user query (which could be in English, Hindi, Marathi, or Hinglish) and output a JSON object with 4 keys:\n"
            '- "detected_lang": detected query language (e.g. "English", "Hindi", "Marathi", "Hinglish")\n'
            '- "english": concise normalized search query in English stripping away conversational filler words (e.g. "kunal deshmukh che aadhar card ahe ka aaplya files madhe?" -> "Kunal Deshmukh Aadhar Card")\n'
            '- "hindi": concise search keywords in Hindi (Devanagari script)\n'
            '- "marathi": concise search keywords in Marathi (Devanagari script)\n'
            "Output ONLY valid JSON. No markdown formatting."
        )
        resp = await llm.complete([
            Message(role="system", content=sys_msg),
            Message(role="user", content=f"Query: {query};")
        ])
        clean_json = resp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(clean_json)
        logger.info("Tri-lingual query expansion for '%s': %s", query, data)
        return {
            "detected_lang": data.get("detected_lang", "English"),
            "english": data.get("english", query),
            "hindi": data.get("hindi", query),
            "marathi": data.get("marathi", query),
        }
    except Exception as e:
        logger.warning("Tri-lingual query expansion failed: %s", e)
        return {"detected_lang": "English", "english": query, "hindi": query, "marathi": query}


async def _generate_trilingual_hyde(query: str, expanded: dict) -> list[str]:
    """Generate realistic hypothetical document excerpts (HyDE) in English, Hindi, and Marathi."""
    try:
        llm = get_llm_provider()
        sys_msg = (
            "You are an AI document intelligence system. Generate realistic, formal 1-sentence hypothetical document excerpts "
            "or record lines that directly answer the query in 3 languages:\n"
            "1. English excerpt\n"
            "2. Hindi excerpt (Devanagari script)\n"
            "3. Marathi excerpt (Devanagari script)\n"
            'Output a JSON list of 3 strings: ["english excerpt", "hindi excerpt", "marathi excerpt"]. Output ONLY valid JSON.'
        )
        resp = await llm.complete([
            Message(role="system", content=sys_msg),
            Message(role="user", content=f"Query: {query}\nEnglish Context: {expanded.get('english')}")
        ])
        clean_json = resp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        snippets = json.loads(clean_json)
        if isinstance(snippets, list) and len(snippets) > 0:
            valid_snippets = [s.strip() for s in snippets if isinstance(s, str) and s.strip()]
            logger.info("Generated Tri-Lingual HyDE snippets for '%s': %s", query, valid_snippets)
            return valid_snippets
        return [expanded.get("english", query), expanded.get("hindi", query), expanded.get("marathi", query)]
    except Exception as e:
        logger.warning("Tri-lingual HyDE generation failed: %s", e)
        return [expanded.get("english", query)]


async def search(
    query: str,
    tenant_id: UUID,
    user_id: UUID,
    limit: int,
    filters: dict | None,
    db: AsyncSession,
    ip_address: str,
    rerank_provider: str | None = None,
    generate_summary: bool = True,
) -> SearchResponse:
    start_time = time.time()

    search_mode = "direct"
    hyde_triggered = False
    hyde_success = False
    hypothetical_snippet = None
    reranked = True
    grounded = True
    
    # 1. Enforce AI Input Guardrails
    from app.services.guardrail_service import validate_input_query, validate_output_summary
    is_safe, error_msg, scrubbed_query = validate_input_query(query)
    if not is_safe:
        took_ms = int((time.time() - start_time) * 1000)
        return SearchResponse(
            query=query,
            ai_summary=f"Safety Block: {error_msg}",
            results=[],
            cached=False,
            took_ms=took_ms,
            search_mode="failed_all",
            hyde_triggered=False,
            reranked=True
        )

    query = scrubbed_query
    
    cache_key = generate_cache_key(str(tenant_id), query, filters)
    cached = await get_cached_search(cache_key)
    if cached:
        return cached
        
    # 2. Tri-Lingual Query Expansion (English, Hindi, Marathi)
    expanded = await _expand_trilingual_query(query)
    detected_lang = expanded.get("detected_lang", "English")
    q_en = expanded.get("english", query)
    q_hi = expanded.get("hindi", query)
    q_mr = expanded.get("marathi", query)
    
    embed_provider = get_embed_provider()
    tri_queries = list(dict.fromkeys([q_en, q_hi, q_mr, query]))
    q_embeddings = await embed_provider.embed(tri_queries)
    
    # Build filter clauses dynamically for hybrid search
    filter_clauses = []
    params = {
        "query_en": q_en,
        "query_mr": q_mr,
        "tenant_id": str(tenant_id),
    }
    
    if filters:
        for idx, (k, v) in enumerate(filters.items()):
            if k == "doc_type":
                filter_clauses.append(f"AND d.doc_type = :filter_{idx}")
                params[f"filter_{idx}"] = str(v)
            elif k == "document_id":
                filter_clauses.append(f"AND d.id = :filter_{idx}")
                params[f"filter_{idx}"] = str(v)
            else:
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
                params[f"filter_key_{idx}"] = str(k)
                params[f"filter_val_{idx}"] = str(v)
                params[f"filter_like_val_{idx}"] = f'%"{v}"%'
                
    filter_str = "\n".join(filter_clauses)
    
    # 3. Vector search (pgvector <=> operator across English, Hindi, Marathi embeddings)
    vec_sql = text(f"""
        SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               1 - (c.embedding <=> CAST(:query_embedding AS vector)) as vector_score
        FROM chunks c 
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN document_versions v ON v.id = d.current_version_id
        WHERE d.tenant_id = CAST(:tenant_id AS uuid) AND d.status = 'indexed' AND d.is_trashed = false {filter_str}
        ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
        LIMIT 20
    """)
    
    all_vec_rows = []
    for q_emb in q_embeddings:
        q_emb_str = "[" + ",".join(str(f) for f in q_emb) + "]"
        vec_res = await db.execute(vec_sql, {**params, "query_embedding": q_emb_str})
        all_vec_rows.extend(vec_res.fetchall())
    
    # 4. Keyword search (English + Simple Unicode for Devanagari Marathi/Hindi)
    kw_sql = text(f"""
        SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               ts_rank(c.content_tsv, q) as keyword_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN document_versions v ON v.id = d.current_version_id,
        COALESCE(
          NULLIF(plainto_tsquery('english', :query_en), ''),
          NULLIF(websearch_to_tsquery('english', :query_en), ''),
          NULLIF(plainto_tsquery('simple', :query_mr), ''),
          plainto_tsquery('simple', :query_en)
        ) q
        WHERE c.content_tsv @@ q AND d.tenant_id = CAST(:tenant_id AS uuid) AND d.status = 'indexed' AND d.is_trashed = false {filter_str}
        ORDER BY keyword_score DESC
        LIMIT 20
    """)
    
    kw_res = await db.execute(kw_sql, params)
    kw_rows = kw_res.fetchall()
    
    # 5. RRF Merge (Reciprocal Rank Fusion across all language vectors and keywords)
    rrf_scores = {}
    docs_map = {}
    k = 60
    
    for rank, row in enumerate(all_vec_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + (rank % 20) + 1))
        
    for rank, row in enumerate(kw_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1))

    merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:20]
    relevant_ranks = []
    if merged:
        reranker = get_rerank_provider(override=rerank_provider)
        doc_texts = [docs_map[cid].content for cid, _ in merged]

        try:
            reranked_primary = await reranker.rerank(query, doc_texts, top_n=limit * 2)
            if q_mr and q_mr != query:
                try:
                    reranked_trans = await reranker.rerank(q_mr, doc_texts, top_n=limit * 2)
                    rank_map = {r.index: r for r in reranked_primary}
                    for r_trans in reranked_trans:
                        if r_trans.index in rank_map:
                            rank_map[r_trans.index].score = max(rank_map[r_trans.index].score, r_trans.score)
                    reranked_primary = list(rank_map.values())
                except Exception as ex:
                    logger.warning("Secondary translation rerank skipped: %s", ex)

            RELEVANCE_THRESHOLD = 0.15
            relevant_ranks = [r for r in reranked_primary if r.score >= RELEVANCE_THRESHOLD]
        except Exception as e:
            logger.error("Reranker unavailable (%s) — falling back to unranked RRF order: %s", reranker.__class__.__name__, e)
            reranked = False
            relevant_ranks = [
                RankedResult(index=i, score=0.0, text=t)
                for i, t in enumerate(doc_texts[:limit * 2])
            ]

        if relevant_ranks:
            vec_cids = {str(r.id) for r in all_vec_rows}
            kw_cids = {str(r.id) for r in kw_rows}
            matched_cids = {str(merged[rank_res.index][0]) for rank_res in relevant_ranks if rank_res.index < len(merged)}
            has_vec = bool(matched_cids & vec_cids)
            has_kw = bool(matched_cids & kw_cids)
            if has_vec and has_kw:
                search_mode = "vector+keyword"
            elif has_vec:
                search_mode = "vector"
            elif has_kw:
                search_mode = "keyword"
            else:
                search_mode = "vector+keyword"

    # --- Step 6: TRI-LINGUAL HYDE AUTOMATIC FALLBACK ---
    if not merged or not relevant_ranks:
        logger.info("Direct tri-lingual search returned 0 matches for '%s'. Triggering Tri-Lingual HyDE Fallback...", query)
        hyde_triggered = True
        hyde_snippets = await _generate_trilingual_hyde(query, expanded)
        hypothetical_snippet = " | ".join(hyde_snippets)
        
        if hyde_snippets:
            try:
                hyde_embeddings = await embed_provider.embed(hyde_snippets)
                hyde_vec_rows = []
                for h_emb in hyde_embeddings:
                    h_emb_str = "[" + ",".join(str(f) for f in h_emb) + "]"
                    h_res = await db.execute(vec_sql, {**params, "query_embedding": h_emb_str})
                    hyde_vec_rows.extend(h_res.fetchall())
                
                if hyde_vec_rows:
                    hyde_rrf_scores = {}
                    hyde_docs_map = {}
                    
                    for rank, row in enumerate(hyde_vec_rows):
                        cid = str(row.id)
                        hyde_docs_map[cid] = row
                        hyde_rrf_scores[cid] = hyde_rrf_scores.get(cid, 0) + (1.0 / (k + (rank % 20) + 1))
                    
                    for rank, row in enumerate(kw_rows):
                        cid = str(row.id)
                        hyde_docs_map[cid] = row
                        hyde_rrf_scores[cid] = hyde_rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1))
                    
                    hyde_merged = sorted(hyde_rrf_scores.items(), key=lambda x: x[1], reverse=True)[:20]
                    if hyde_merged:
                        reranker = get_rerank_provider(override=rerank_provider)
                        doc_texts = [hyde_docs_map[cid].content for cid, _ in hyde_merged]

                        try:
                            reranked_primary = await reranker.rerank(query, doc_texts, top_n=limit * 2)
                            if q_mr and q_mr != query:
                                try:
                                    reranked_trans = await reranker.rerank(q_mr, doc_texts, top_n=limit * 2)
                                    rank_map = {r.index: r for r in reranked_primary}
                                    for r_trans in reranked_trans:
                                        if r_trans.index in rank_map:
                                            rank_map[r_trans.index].score = max(rank_map[r_trans.index].score, r_trans.score)
                                    reranked_primary = list(rank_map.values())
                                except Exception as ex:
                                    logger.warning("Secondary translation HyDE rerank skipped: %s", ex)

                            RELEVANCE_THRESHOLD = 0.15
                            relevant_ranks = [r for r in reranked_primary if r.score >= RELEVANCE_THRESHOLD]
                        except Exception as e:
                            logger.error("Reranker unavailable (%s) — falling back to unranked RRF order: %s", reranker.__class__.__name__, e)
                            reranked = False
                            relevant_ranks = [
                                RankedResult(index=i, score=0.0, text=t)
                                for i, t in enumerate(doc_texts[:limit * 2])
                            ]

                        if relevant_ranks:
                            merged = hyde_merged
                            docs_map = hyde_docs_map
                            search_mode = "HyDE"
                            hyde_success = True
                            logger.info("Tri-Lingual HyDE Fallback SUCCESS: Found %d matching candidate(s)", len(relevant_ranks))
                        else:
                            logger.info("HyDE candidates scored below relevance threshold (0.15). Yielding 0 results.")
            except Exception as e:
                logger.error("Tri-Lingual HyDE fallback vector search failed: %s", e)

    # If still no matches after Direct + HyDE Fallback
    if not merged or not relevant_ranks:
        if hyde_triggered:
            search_mode = "failed_all"
            hyde_success = False
            
        if filters and "document_id" in filters:
            doc_id_param = str(filters["document_id"])
            try:
                target_doc_id = UUID(doc_id_param)
            except ValueError:
                target_doc_id = None

            if target_doc_id:
                chunk_sql = text("""
                    SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    LEFT JOIN document_versions v ON v.id = d.current_version_id
                    WHERE d.id = :target_doc_id AND d.tenant_id = CAST(:tenant_id AS uuid) AND d.is_trashed = false
                    ORDER BY c.page_number ASC, c.chunk_index ASC
                    LIMIT 30
                """)
                chunk_res = await db.execute(chunk_sql, {"target_doc_id": target_doc_id, "tenant_id": str(tenant_id)})
                doc_chunk_rows = chunk_res.fetchall()

                snippets_for_llm = []
                fallback_results = []

                if doc_chunk_rows:
                    for r in doc_chunk_rows:
                        s3_path = r.s3_path
                        url = await generate_presigned_url(s3_path) if s3_path else ""
                        fallback_results.append(SearchResult(
                            document_id=r.doc_id,
                            document_name=r.title,
                            download_url=url,
                            page_number=r.page_number,
                            snippet=_make_snippet(r.content),
                            score=1.0,
                            metadata={}
                        ))
                        snippets_for_llm.append(f"Document: {r.title} (Page {r.page_number or 1})\nExcerpt: {r.content}")

                if snippets_for_llm:
                    if not generate_summary:
                        summary = (
                            "AI summary generation is disabled for this search (testing mode). "
                            "Raw retrieved excerpts are shown below."
                        )
                    else:
                        try:
                            llm = get_llm_provider()
                            sys_msg = (
                                "You are an enterprise document intelligence assistant. Answer the user's question accurately, naturally, and professionally using ONLY the provided document excerpts.\n"
                                "- Highlight key numbers, prices, dates, names, policies, and terms in bold formatting.\n"
                                "- Organize information with clean bullet points or numbered lists where appropriate.\n"
                                "- If asked to summarize, give a clear, comprehensive summary of the document's contents.\n"
                                "- Do NOT invent details outside the provided excerpts."
                            )
                            user_msg = f"Question: {query}\n\nDocument Contents:\n" + "\n---\n".join(snippets_for_llm)
                            summary = await llm.complete([
                                Message(role="system", content=sys_msg),
                                Message(role="user", content=user_msg)
                            ])
                            summary = validate_output_summary(summary)
                        except Exception as e:
                            logger.warning("AI summary unavailable for document preview: %s", e)
                            summary = (
                                f"Found {len(fallback_results)} matching page(s) for '{query}'. "
                                "AI summary is temporarily unavailable — the excerpts below are unedited source text."
                            )

                    took_ms = int((time.time() - start_time) * 1000)
                    resp = SearchResponse(
                        query=query,
                        ai_summary=summary,
                        results=fallback_results,
                        cached=False,
                        took_ms=took_ms,
                        search_mode=search_mode,
                        hyde_triggered=hyde_triggered,
                        reranked=True,
                        grounded=True
                    )
                    await log_action(
                        db,
                        user_id,
                        tenant_id,
                        "search.query",
                        details={
                            "query": query,
                            "search_mode": search_mode,
                            "hyde_triggered": hyde_triggered,
                            "hyde_success": hyde_success,
                            "hypothetical_snippet": hypothetical_snippet,
                            "result_count": len(fallback_results),
                            "took_ms": took_ms
                        },
                        ip_address=ip_address
                    )
                    return resp

        took_ms = int((time.time() - start_time) * 1000)

        # Check if any documents in this tenant are currently being indexed
        pending_sql = text("SELECT title FROM documents WHERE tenant_id = CAST(:tenant_id AS uuid) AND status IN ('pending', 'processing') AND is_trashed = false LIMIT 3")
        pending_res = await db.execute(pending_sql, {"tenant_id": str(tenant_id)})
        pending_titles = [r.title for r in pending_res.fetchall()]

        if pending_titles:
            titles_str = ", ".join([f"'{t}'" for t in pending_titles])
            summary_text = (
                f"No indexed matches found for '{query}'.\n\n"
                f"ℹ️ **AI Indexing Notice**: {len(pending_titles)} document(s) ({titles_str}) are currently being processed in the background (OCR, text chunking, and 1024d vector embedding generation). Please wait a few seconds for indexing to finish and search again."
            )
        else:
            summary_text = f"No matching documents were found in your drive for '{query}'."

        resp = SearchResponse(
            query=query,
            ai_summary=summary_text,
            results=[],
            cached=False,
            took_ms=took_ms,
            search_mode=search_mode,
            hyde_triggered=hyde_triggered,
            reranked=True,
            grounded=True
        )
        await log_action(
            db,
            user_id,
            tenant_id,
            "search.query",
            details={
                "query": query,
                "search_mode": search_mode,
                "hyde_triggered": hyde_triggered,
                "hyde_success": hyde_success,
                "hypothetical_snippet": hypothetical_snippet,
                "result_count": 0,
                "took_ms": took_ms
            },
            ip_address=ip_address
        )
        return resp
        
    final_results = []
    snippets_for_llm = []
    doc_ids_for_metadata = []
    seen_dedup = set()
    
    for rank_res in relevant_ranks:
        idx = rank_res.index
        cid, _ = merged[idx]
        row = docs_map[cid]
        
        # Deduplicate identical document page matches
        dedup_key = (row.doc_id, row.page_number)
        if dedup_key in seen_dedup:
            continue
        seen_dedup.add(dedup_key)
        
        doc_ids_for_metadata.append(row.doc_id)
        
        if len(final_results) >= limit:
            break
            
    # Query metadata for returned documents (Task 6.4)
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
            
    seen_dedup.clear()
    for rank_res in relevant_ranks:
        idx = rank_res.index
        cid, _ = merged[idx]
        row = docs_map[cid]
        
        dedup_key = (row.doc_id, row.page_number)
        if dedup_key in seen_dedup:
            continue
        seen_dedup.add(dedup_key)
        
        s3_path = row.s3_path
        url = await generate_presigned_url(s3_path) if s3_path else ""
        
        final_results.append(SearchResult(
            document_id=row.doc_id,
            document_name=row.title,
            download_url=url,
            page_number=row.page_number,
            snippet=_make_snippet(row.content),
            score=rank_res.score,
            metadata=meta_map.get(row.doc_id, {})
        ))
        snippets_for_llm.append(f"Document: {row.title} (Page {row.page_number or 1})\nExcerpt: {row.content}")
        
        if len(final_results) >= limit:
            break
            
    # 7. Generate Natural, Professional AI Summary using LLM
    if not generate_summary:
        summary = (
            f"Found {len(final_results)} matching document(s) for '{query}'. "
            "AI summary generation is disabled for this search (testing mode)."
        )
    else:
        try:
            llm = get_llm_provider()
            sys_msg = (
                "You are an enterprise multilingual document intelligence assistant. Answer the user's question accurately, naturally, and professionally using ONLY the provided document excerpts.\n"
                f"- Synthesize your entire response in the user's detected query language ({detected_lang}).\n"
                "- Highlight key numbers, policies, dates, and names in bold formatting.\n"
                "- Organize information with clean bullet points or numbered lists where appropriate.\n"
                "- Do NOT invent details outside the excerpts.\n"
                "- After your full answer, on a new line by itself, output exactly [GROUNDED:true] if the excerpts actually contained information answering the question, "
                "or [GROUNDED:false] if they did not contain relevant information and you had to decline. Do not explain this marker, just append it."
            )
            user_msg = f"Question: {query}\n\nRelevant Document Excerpts:\n" + "\n---\n".join(snippets_for_llm)
            raw_summary = await llm.complete([
                Message(role="system", content=sys_msg),
                Message(role="user", content=user_msg)
            ])
            raw_summary = raw_summary.strip()
            marker_match = re.search(r'\[GROUNDED:\s*(true|false)\s*\]\s*$', raw_summary, re.IGNORECASE)
            if marker_match:
                grounded = marker_match.group(1).lower() == "true"
                raw_summary = raw_summary[:marker_match.start()].rstrip()
            summary = validate_output_summary(raw_summary)
        except Exception as e:
            logger.warning("AI summary unavailable: %s", e)
            summary = (
                f"Found {len(final_results)} matching document(s) for '{query}'. "
                "AI summary is temporarily unavailable — the excerpts below are unedited source text."
            )
    
    took_ms = int((time.time() - start_time) * 1000)
    
    resp = SearchResponse(
        query=query,
        ai_summary=summary,
        results=final_results,
        cached=False,
        took_ms=took_ms,
        search_mode=search_mode,
        hyde_triggered=hyde_triggered,
        reranked=reranked,
        grounded=grounded
    )
    
    # Audit log & Cache
    await log_action(
        db,
        user_id,
        tenant_id,
        "search.query",
        details={
            "query": query,
            "search_mode": search_mode,
            "hyde_triggered": hyde_triggered,
            "hyde_success": hyde_success,
            "hypothetical_snippet": hypothetical_snippet,
            "result_count": len(final_results),
            "took_ms": took_ms
        },
        ip_address=ip_address
    )
    await cache_search_result(cache_key, resp)
    
    return resp
