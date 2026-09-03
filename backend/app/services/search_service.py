import time
import re
import logging
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.schemas.search import SearchResponse, SearchResult, Citation
from app.services.cache_service import get_cached_search, cache_search_result, generate_cache_key
from app.services.audit_service import log_action
from app.services.storage_service import generate_presigned_url
import json
from app.ai.factory import get_embed_provider, get_rerank_provider, get_llm_provider
from app.ai.base import Message, RankedResult
from app.models.metadata_item import MetadataItem
from app.services.config_service import get_int, get_float
from app.services.search_glossary_service import expand_query_terms

logger = logging.getLogger(__name__)


def _make_snippet(content: str, max_chars: int = 400) -> str:
    """Truncate result snippet around boundary to keep payload light."""
    if not content or len(content) <= max_chars:
        return content or ""
    return content[:max_chars].rsplit(" ", 1)[0] + "…"


async def _find_pending_title_matches(
    db: AsyncSession, tenant_id: UUID, query: str, exclude_doc_ids: set
) -> List[SearchResult]:
    """T74 — a document must be findable by metadata before indexing finishes.

    Content search filters on status='indexed', so a still-processing
    document is otherwise invisible until Celery catches up. This matches
    by title alone (no chunks exist yet for a pending document) and marks
    the result as pending so the caller can show it's still being indexed.
    """
    stmt = text("""
        SELECT d.id, d.title, d.status, v.s3_path
        FROM doc_dg_documents d
        LEFT JOIN doc_dg_document_versions v ON v.id = d.current_version_id
        WHERE d.tenant_id = CAST(:tenant_id AS uuid)
          AND d.is_trashed = false
          AND d.status IN ('pending', 'processing')
          AND d.title ILIKE :title_pattern
        LIMIT 5
    """)
    res = await db.execute(stmt, {"tenant_id": str(tenant_id), "title_pattern": f"%{query}%"})
    rows = res.fetchall()

    matches = []
    for row in rows:
        if row.id in exclude_doc_ids:
            continue
        url = await generate_presigned_url(row.s3_path) if row.s3_path else ""
        matches.append(SearchResult(
            document_id=row.id,
            document_name=row.title,
            download_url=url,
            page_number=None,
            snippet="This document is still being processed (OCR, chunking, embedding) — full-text search will include it shortly.",
            score=0.0,
            metadata={"pending": True, "status": row.status},
        ))
    return matches


def _parse_claims_json(raw: str):
    """Best-effort parse of the LLM's structured claim response — tolerates
    ```json fences the model adds despite being told not to."""
    raw = raw.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


async def _generate_grounded_answer(query: str, detected_lang: str, excerpts: list):
    """T70 — bind every claim in the answer to the excerpt(s) that actually
    support it, and refuse outright when the excerpts don't answer the
    question. This is the product's hard rule (Section 8): a confident,
    well-sourced-*looking* answer with nothing behind it is the exact
    failure this gate exists to prevent — so an unsupported claim is
    dropped, not shown, and an unanswerable question gets no answer at all
    rather than a plausible-sounding guess.

    Returns (summary_text_or_None, citations, grounded).
    """
    llm = get_llm_provider()

    numbered = "\n\n".join(
        f"[{i + 1}] Document: {e['document_name']} (Page {e['page_number'] or 1})\n{e['content']}"
        for i, e in enumerate(excerpts)
    )

    sys_msg = (
        "You are an enterprise multilingual document intelligence assistant. "
        "Answer strictly and only from the numbered excerpts below — never from outside knowledge.\n"
        f"Respond in the user's detected query language ({detected_lang}).\n\n"
        "The user's query may be a natural-language question (\"what is the salary of X\") OR a short "
        "keyword/name/phrase search (\"Aurangabad-Shia\", a document title, a place or person name). For a "
        "keyword/phrase query, treat it as \"summarize what these excerpts say that is relevant to this topic\" "
        "rather than requiring a literal question to be answered.\n\n"
        'Respond with ONLY a single JSON object, no markdown fences, no other text, in this exact shape:\n'
        '{"answerable": true, "claims": [{"text": "one factual statement", "sources": [1, 2]}]}\n\n'
        "Rules:\n"
        "- Break your answer into individual factual claims. Each claim's \"sources\" must list every excerpt "
        "number that actually supports it. Never cite an excerpt that does not contain the stated fact.\n"
        '- Respond with {"answerable": false, "claims": []} ONLY if the excerpts are unrelated to the query '
        "topic — not merely because the query isn't phrased as a question. Do not answer from outside knowledge "
        "and do not guess — this is a hard rule, not a style preference.\n"
        "- Keep claim text natural and complete; bold key numbers/names/dates with **markdown** where useful."
    )
    user_msg = f"User query: {query}\n\nNumbered excerpts:\n{numbered}"

    raw = await llm.complete([
        Message(role="system", content=sys_msg),
        Message(role="user", content=user_msg),
    ], max_tokens=2500)

    parsed = _parse_claims_json(raw)
    if not parsed or not parsed.get("answerable") or not parsed.get("claims"):
        return None, [], False

    summary_lines = []
    citations = []
    # T71: number citations by unique (document, page) — not by excerpt index —
    # so two excerpts from the same page share one marker instead of two.
    source_number_by_key: dict = {}

    for claim in parsed["claims"]:
        claim_text = str(claim.get("text", "")).strip()
        sources = claim.get("sources", [])
        if not claim_text or not isinstance(sources, list):
            continue
        valid_sources = [s for s in sources if isinstance(s, int) and 1 <= s <= len(excerpts)]
        if not valid_sources:
            # The model cited nothing real for this claim — drop the claim
            # rather than show an unbound statement.
            continue
        claim_numbers = []
        for s in valid_sources:
            ex = excerpts[s - 1]
            key = (ex["document_id"], ex["page_number"])
            if key not in source_number_by_key:
                source_number_by_key[key] = len(source_number_by_key) + 1
            n = source_number_by_key[key]
            if n not in claim_numbers:
                claim_numbers.append(n)
            citations.append(Citation(
                number=n,
                claim=claim_text,
                document_id=ex["document_id"],
                document_name=ex["document_name"],
                page_number=ex["page_number"],
                chunk_id=ex.get("chunk_id"),
                fact_id=ex.get("fact_id"),
            ))

        markers = "".join(f" [{n}]" for n in sorted(claim_numbers))
        summary_lines.append(f"- {claim_text}{markers}")

    if not summary_lines:
        return None, [], False

    return "\n".join(summary_lines), citations, True


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
    from app.services.guardrail_service import validate_input_query
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
    
    # TS7 — glossary-first cross-script expansion: free, local, always
    # available (unlike the LLM expansion above, which silently degrades
    # to the raw query on any failure, including air-gapped mode). Only
    # ever adds vector-search variants (see search_glossary_service.py's
    # docstring for why this doesn't touch the keyword-search legs).
    glossary_terms = await expand_query_terms(db, query)

    embed_provider = get_embed_provider()
    tri_queries = list(dict.fromkeys([q_en, q_hi, q_mr, query, *glossary_terms]))
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
                # T73 — a filter key can match either the generic LLM
                # metadata pass (title/author/date/type/topics/summary) or
                # a template-extracted structured field (area, village,
                # status...) on doc_dg_facts. Either source satisfying it
                # is enough — a document doesn't need both.
                filter_clauses.append(f"""
                    AND (
                      EXISTS (
                        SELECT 1 FROM doc_dg_metadata_items m
                        WHERE m.document_id = d.id
                          AND m.key = :filter_key_{idx}
                          AND (
                            m.value->>'v' = :filter_val_{idx}
                            OR m.value->> :filter_key_{idx} = :filter_val_{idx}
                            OR m.value::text = :filter_val_{idx}
                            OR m.value::text LIKE :filter_like_val_{idx}
                          )
                      )
                      OR EXISTS (
                        SELECT 1 FROM doc_dg_facts f2
                        WHERE f2.document_id = d.id
                          AND f2.field_name = :filter_key_{idx}
                          AND COALESCE(f2.value->>'v', f2.value::text) = :filter_val_{idx}
                      )
                    )
                """)
                params[f"filter_key_{idx}"] = str(k)
                params[f"filter_val_{idx}"] = str(v)
                params[f"filter_like_val_{idx}"] = f'%"{v}"%'
                
    filter_str = "\n".join(filter_clauses)
    candidate_limit = await get_int("search_candidate_limit", 20)

    # 3. Vector search (pgvector <=> operator across English, Hindi, Marathi embeddings)
    vec_sql = text(f"""
        SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               1 - (c.embedding <=> CAST(:query_embedding AS vector)) as vector_score
        FROM doc_dg_chunks c
        JOIN doc_dg_documents d ON c.document_id = d.id
        LEFT JOIN doc_dg_document_versions v ON v.id = d.current_version_id
        WHERE d.tenant_id = CAST(:tenant_id AS uuid) AND d.status = 'indexed' AND d.is_trashed = false {filter_str}
        ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
        LIMIT {candidate_limit}
    """)

    all_vec_rows = []
    for q_emb in q_embeddings:
        q_emb_str = "[" + ",".join(str(f) for f in q_emb) + "]"
        vec_res = await db.execute(vec_sql, {**params, "query_embedding": q_emb_str})
        all_vec_rows.extend(vec_res.fetchall())

    # 4. Keyword search — English (stemmed) and Devanagari/Marathi (unstemmed
    # 'simple' config) are searched against their own matching tsvector column
    # (T75): a 'simple' query against an 'english'-stemmed vector silently
    # drops matches, since english config removes stopwords and stems words
    # the simple-config query never touched.
    kw_sql = text(f"""
        SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               GREATEST(ts_rank(c.content_tsv, q_en), ts_rank(c.content_tsv_simple, q_simple)) as keyword_score
        FROM doc_dg_chunks c
        JOIN doc_dg_documents d ON c.document_id = d.id
        LEFT JOIN doc_dg_document_versions v ON v.id = d.current_version_id,
        COALESCE(
          NULLIF(plainto_tsquery('english', :query_en), ''),
          NULLIF(websearch_to_tsquery('english', :query_en), ''),
          ''::tsquery
        ) q_en,
        COALESCE(
          NULLIF(plainto_tsquery('simple', :query_mr), ''),
          NULLIF(plainto_tsquery('simple', :query_en), ''),
          ''::tsquery
        ) q_simple
        WHERE (c.content_tsv @@ q_en OR c.content_tsv_simple @@ q_simple)
          AND d.tenant_id = CAST(:tenant_id AS uuid) AND d.status = 'indexed' AND d.is_trashed = false {filter_str}
        ORDER BY keyword_score DESC
        LIMIT {candidate_limit}
    """)
    
    kw_res = await db.execute(kw_sql, params)
    kw_rows = kw_res.fetchall()

    # 4b. Fuzzy/trigram search (T72) — catches misspellings vector search's
    # semantics and keyword search's exact tokens both miss (a typo'd proper
    # noun like "Depshmukh" for "Deshmukh"). word_similarity(), not plain
    # similarity(): matching a short query against a whole chunk of running
    # text with similarity() dilutes the score against chunk length (a real
    # substring match scored ~0.2); word_similarity() finds the best-matching
    # substring instead and scored the same case at 1.0. The threshold is a
    # GUC, not a bind param — SET LOCAL only accepts literals, but this value
    # comes from sys_dg_config, never from the request, so interpolating it
    # is safe. LOCAL keeps it scoped to this transaction, not the pooled
    # connection.
    trgm_threshold = await get_float("search_trigram_threshold", 0.3)
    await db.execute(text(f"SET LOCAL pg_trgm.word_similarity_threshold = {trgm_threshold}"))
    trgm_sql = text(f"""
        SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path,
               word_similarity(:query_en, c.content) as trigram_score
        FROM doc_dg_chunks c
        JOIN doc_dg_documents d ON c.document_id = d.id
        LEFT JOIN doc_dg_document_versions v ON v.id = d.current_version_id
        WHERE d.tenant_id = CAST(:tenant_id AS uuid) AND d.status = 'indexed' AND d.is_trashed = false {filter_str}
          AND :query_en <% c.content
        ORDER BY trigram_score DESC
        LIMIT {candidate_limit}
    """)
    trgm_res = await db.execute(trgm_sql, params)
    trgm_rows = trgm_res.fetchall()

    # 4c. Structured-record search (T73) — extracted Fact fields, not only
    # chunk text. A user might ask about a value that only exists as an
    # extracted field (owner_name, valuation, survey_no...) and never
    # verbatim as running chunk text the way OCR read the page. Marginalia
    # (field_name="_marginalia", T30) is deliberately excluded — those are
    # free-floating adjudication notes, not extracted record fields.
    # Shaped identically to the chunk legs above (same column names) so it
    # drops into the exact same RRF/rerank/results pipeline unchanged;
    # fact_row_ids (below) is how downstream code tells a fact row from a
    # chunk row apart, the same way vec_cids/kw_cids/trgm_cids already
    # track each leg's origin for search_mode.
    # The raw, un-expanded query — not q_en. Trilingual expansion is a
    # semantic reformulation (T73's own test caught this: it turned
    # "42/1B-Kolhapur" into "42/1B Kolhapur", hyphen to space), which is
    # fine for vector/keyword search but wrong here — a structured field
    # like a survey number or an ID is exactly the kind of literal text a
    # paraphrase shouldn't be allowed to alter before matching it.
    fact_pattern = f"%{query}%"
    fact_sql = text(f"""
        SELECT f.id, (f.field_name || ': ' || COALESCE(f.value->>'v', f.value::text)) as content,
               fact_page.page_number as page_number, 0 as chunk_index,
               d.title, d.id as doc_id, v.s3_path
        FROM doc_dg_facts f
        JOIN doc_dg_documents d ON f.document_id = d.id
        LEFT JOIN doc_dg_document_versions v ON v.id = d.current_version_id
        LEFT JOIN LATERAL (
            SELECT p.page_number FROM doc_dg_fact_regions fr
            JOIN doc_dg_pages p ON p.id = fr.page_id
            WHERE fr.fact_id = f.id
            ORDER BY p.page_number ASC LIMIT 1
        ) fact_page ON true
        WHERE f.tenant_id = CAST(:tenant_id AS uuid) AND d.status = 'indexed' AND d.is_trashed = false
          AND f.field_name != '_marginalia'
          AND (f.field_name ILIKE :fact_pattern OR COALESCE(f.value->>'v', f.value::text) ILIKE :fact_pattern)
          {filter_str}
        ORDER BY f.confidence DESC NULLS LAST
        LIMIT {candidate_limit}
    """)
    fact_res = await db.execute(fact_sql, {**params, "fact_pattern": fact_pattern})
    fact_rows = fact_res.fetchall()
    fact_row_ids = {str(r.id) for r in fact_rows}

    # 5. RRF Merge (Reciprocal Rank Fusion across all language vectors, keywords, fuzzy, and structured matches)
    rrf_scores = {}
    docs_map = {}
    k = await get_int("search_rrf_k", 60)

    for rank, row in enumerate(all_vec_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + (rank % candidate_limit) + 1))

    for rank, row in enumerate(kw_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1))

    for rank, row in enumerate(trgm_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1))

    for rank, row in enumerate(fact_rows):
        cid = str(row.id)
        docs_map[cid] = row
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank + 1))

    merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:20]
    relevant_ranks = []
    if merged:
        reranker = get_rerank_provider(override=rerank_provider)
        doc_texts = [docs_map[cid].content for cid, _ in merged]

        try:
            # Real bug found live 2026-09-03: rerank(..., top_n=limit*2) only
            # returns each call's OWN top slice. A document scoring near-zero
            # under the raw query but highly relevant under its translation
            # (exactly the cross-script case this second pass exists for)
            # isn't IN reranked_primary at all, so "if r_trans.index in
            # rank_map" silently dropped it instead of adding it — verified
            # live: a Marathi document scored 0.55 under the translated
            # rerank (well above the 0.15 threshold) but was discarded here
            # every time, making cross-script search fail on every query
            # whose translation-relevant document wasn't already primary-
            # relevant. top_n=len(doc_texts) scores every candidate under
            # both queries, and the merge now adds a translated-only hit
            # instead of requiring it to already exist.
            reranked_primary = await reranker.rerank(query, doc_texts, top_n=len(doc_texts))
            if q_mr and q_mr != query:
                try:
                    reranked_trans = await reranker.rerank(q_mr, doc_texts, top_n=len(doc_texts))
                    rank_map = {r.index: r for r in reranked_primary}
                    for r_trans in reranked_trans:
                        if r_trans.index in rank_map:
                            rank_map[r_trans.index].score = max(rank_map[r_trans.index].score, r_trans.score)
                        else:
                            rank_map[r_trans.index] = r_trans
                    reranked_primary = list(rank_map.values())
                except Exception as ex:
                    logger.warning("Secondary translation rerank skipped: %s", ex)

            RELEVANCE_THRESHOLD = await get_float("search_relevance_threshold", 0.15)
            relevant_ranks = sorted(
                (r for r in reranked_primary if r.score >= RELEVANCE_THRESHOLD),
                key=lambda r: r.score, reverse=True,
            )
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
            trgm_cids = {str(r.id) for r in trgm_rows}
            matched_cids = {str(merged[rank_res.index][0]) for rank_res in relevant_ranks if rank_res.index < len(merged)}
            contributing_legs = []
            if matched_cids & vec_cids:
                contributing_legs.append("vector")
            if matched_cids & kw_cids:
                contributing_legs.append("keyword")
            if matched_cids & trgm_cids:
                contributing_legs.append("fuzzy")
            if matched_cids & fact_row_ids:
                contributing_legs.append("structured")
            search_mode = "+".join(contributing_legs) if contributing_legs else "vector+keyword"

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
                            # Same cross-script merge fix as the direct-search
                            # pass above — see that comment for the root cause.
                            reranked_primary = await reranker.rerank(query, doc_texts, top_n=len(doc_texts))
                            if q_mr and q_mr != query:
                                try:
                                    reranked_trans = await reranker.rerank(q_mr, doc_texts, top_n=len(doc_texts))
                                    rank_map = {r.index: r for r in reranked_primary}
                                    for r_trans in reranked_trans:
                                        if r_trans.index in rank_map:
                                            rank_map[r_trans.index].score = max(rank_map[r_trans.index].score, r_trans.score)
                                        else:
                                            rank_map[r_trans.index] = r_trans
                                    reranked_primary = list(rank_map.values())
                                except Exception as ex:
                                    logger.warning("Secondary translation HyDE rerank skipped: %s", ex)

                            RELEVANCE_THRESHOLD = await get_float("search_relevance_threshold", 0.15)
                            relevant_ranks = sorted(
                                (r for r in reranked_primary if r.score >= RELEVANCE_THRESHOLD),
                                key=lambda r: r.score, reverse=True,
                            )
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
                            logger.info("HyDE candidates scored below relevance threshold (%.2f). Yielding 0 results.", RELEVANCE_THRESHOLD)
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
                    FROM doc_dg_chunks c
                    JOIN doc_dg_documents d ON c.document_id = d.id
                    LEFT JOIN doc_dg_document_versions v ON v.id = d.current_version_id
                    WHERE d.id = :target_doc_id AND d.tenant_id = CAST(:tenant_id AS uuid) AND d.is_trashed = false
                    ORDER BY c.page_number ASC, c.chunk_index ASC
                    LIMIT 30
                """)
                chunk_res = await db.execute(chunk_sql, {"target_doc_id": target_doc_id, "tenant_id": str(tenant_id)})
                doc_chunk_rows = chunk_res.fetchall()

                excerpts = []
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
                        excerpts.append({
                            "document_id": r.doc_id,
                            "document_name": r.title,
                            "page_number": r.page_number,
                            "chunk_id": r.id,
                            "content": r.content,
                        })

                if excerpts:
                    citations = []
                    doc_grounded = True
                    if not generate_summary:
                        summary = (
                            "AI summary generation is disabled for this search (testing mode). "
                            "Raw retrieved excerpts are shown below."
                        )
                    else:
                        try:
                            summary, citations, doc_grounded = await _generate_grounded_answer(query, "English", excerpts)
                            if summary is None:
                                summary = "The document does not contain information that answers this question."
                            else:
                                doc_url_by_id = {r.document_id: r.download_url for r in fallback_results}
                                for c in citations:
                                    c.download_url = doc_url_by_id.get(c.document_id)
                        except Exception as e:
                            logger.warning("AI summary unavailable for document preview: %s", e)
                            summary = (
                                f"Found {len(fallback_results)} matching page(s) for '{query}'. "
                                "AI summary is temporarily unavailable — the excerpts below are unedited source text."
                            )
                            doc_grounded = False

                    took_ms = int((time.time() - start_time) * 1000)
                    resp = SearchResponse(
                        query=query,
                        ai_summary=summary,
                        results=fallback_results,
                        citations=citations,
                        refused=not doc_grounded,
                        cached=False,
                        took_ms=took_ms,
                        search_mode=search_mode,
                        hyde_triggered=hyde_triggered,
                        reranked=True,
                        grounded=doc_grounded
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

        # T74: a document must be findable by metadata before indexing
        # finishes — try a title match against still-processing documents
        # before falling back to a generic "nothing found" message.
        title_matches = await _find_pending_title_matches(db, tenant_id, query, exclude_doc_ids=set())

        if title_matches:
            summary_text = (
                f"Found {len(title_matches)} matching document(s) by name for '{query}', "
                f"still being indexed — full-text search will include them shortly."
            )
        else:
            pending_preview_limit = await get_int("search_pending_docs_preview_limit", 3)
            pending_sql = text(f"SELECT title FROM doc_dg_documents WHERE tenant_id = CAST(:tenant_id AS uuid) AND status IN ('pending', 'processing') AND is_trashed = false LIMIT {pending_preview_limit}")
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
            results=title_matches,
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
                "result_count": len(title_matches),
                "took_ms": took_ms
            },
            ip_address=ip_address
        )
        return resp
        
    final_results = []
    excerpts = []
    doc_ids_for_metadata = []
    seen_dedup = set()
    
    for rank_res in relevant_ranks:
        idx = rank_res.index
        cid, _ = merged[idx]
        row = docs_map[cid]
        
        # Deduplicate identical document page matches — except a fact
        # result (T73), which never dedupes against a chunk (or another
        # fact) sharing its page: it's a distinct extracted field, not a
        # near-duplicate snippet the way two chunks on the same page are.
        dedup_key = (row.doc_id, cid) if cid in fact_row_ids else (row.doc_id, row.page_number)
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
        
        # T73 — a fact result never dedupes against a chunk (or another
        # fact) sharing its page: it's a distinct extracted field, not a
        # near-duplicate snippet the way two chunks on the same page are.
        dedup_key = (row.doc_id, cid) if cid in fact_row_ids else (row.doc_id, row.page_number)
        if dedup_key in seen_dedup:
            continue
        seen_dedup.add(dedup_key)
        
        s3_path = row.s3_path
        url = await generate_presigned_url(s3_path) if s3_path else ""

        # T73 — a fact-leg row shares docs_map/RRF with chunk rows (same
        # column shape) but is cited by fact_id, not chunk_id: it points
        # at one extracted field, not a page of running text.
        is_fact = cid in fact_row_ids
        result_metadata = dict(meta_map.get(row.doc_id, {}))
        if is_fact:
            result_metadata["fact_id"] = cid

        final_results.append(SearchResult(
            document_id=row.doc_id,
            document_name=row.title,
            download_url=url,
            page_number=row.page_number,
            snippet=_make_snippet(row.content),
            score=rank_res.score,
            metadata=result_metadata
        ))
        excerpts.append({
            "document_id": row.doc_id,
            "document_name": row.title,
            "page_number": row.page_number,
            "chunk_id": None if is_fact else row.id,
            "fact_id": row.id if is_fact else None,
            "content": row.content,
        })

        if len(final_results) >= limit:
            break

    # T74: also surface any still-processing documents whose title matches —
    # findable by metadata immediately, not just once indexing finishes.
    already_found = {r.document_id for r in final_results}
    final_results.extend(await _find_pending_title_matches(db, tenant_id, query, exclude_doc_ids=already_found))

    # 7. Generate the AI answer — T70: every claim bound to a source excerpt,
    # refuse outright rather than guess when the excerpts don't answer it.
    citations = []
    refused = False
    if not generate_summary:
        summary = (
            f"Found {len(final_results)} matching document(s) for '{query}'. "
            "AI summary generation is disabled for this search (testing mode)."
        )
    else:
        try:
            summary, citations, grounded = await _generate_grounded_answer(query, detected_lang, excerpts)
            if summary is None:
                summary = f"The documents do not contain information that answers '{query}'."
                refused = True
            else:
                doc_url_by_id = {r.document_id: r.download_url for r in final_results}
                for c in citations:
                    c.download_url = doc_url_by_id.get(c.document_id)
        except Exception as e:
            logger.warning("AI summary unavailable: %s", e)
            summary = (
                f"Found {len(final_results)} matching document(s) for '{query}'. "
                "AI summary is temporarily unavailable — the excerpts below are unedited source text."
            )
            grounded = False

    took_ms = int((time.time() - start_time) * 1000)

    resp = SearchResponse(
        query=query,
        ai_summary=summary,
        results=final_results,
        citations=citations,
        refused=refused,
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
    cache_ttl = await get_int("search_cache_ttl_seconds", 300)
    await cache_search_result(cache_key, resp, ttl=cache_ttl)
    
    return resp
