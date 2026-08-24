import re
import json
from uuid import UUID
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload


from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.schemas.search import SearchResult, SearchResponse
from app.services.search_service import search as do_search
from app.services.audit_service import log_action
from app.ai.factory import get_llm_provider
from app.ai.base import Message

async def create_chat_session(
    tenant_id: UUID,
    user_id: UUID,
    title: Optional[str],
    db: AsyncSession
) -> ChatSession:
    session_title = title.strip() if title and title.strip() else "New Persistent Chat"
    session = ChatSession(
        tenant_id=tenant_id,
        user_id=user_id,
        title=session_title
    )
    db.add(session)
    await db.commit()

    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session.id)
    )
    res = await db.execute(stmt)
    return res.scalars().first()



async def list_chat_sessions(
    tenant_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> List[Dict[str, Any]]:
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.tenant_id == tenant_id, ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        items.append({
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "message_count": len(s.messages)
        })
    return items

async def get_chat_session(
    session_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> Optional[ChatSession]:
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .execution_options(populate_existing=True)
        .where(
            ChatSession.id == session_id,
            ChatSession.tenant_id == tenant_id,
            ChatSession.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_chat_session(
    session_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> bool:
    session = await get_chat_session(session_id, tenant_id, user_id, db)
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True

async def update_chat_session_title(
    session_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    title: str,
    db: AsyncSession
) -> Optional[ChatSession]:
    session = await get_chat_session(session_id, tenant_id, user_id, db)
    if not session:
        return None
    session.title = title.strip()
    await db.commit()
    return await get_chat_session(session_id, tenant_id, user_id, db)


def _extract_score_threshold(query: str) -> Optional[float]:
    """
    Parses prompts like 'score >= 85', 'score > 80%', 'score >= 0.85', 'score higher than 90'
    Returns score normalized to float [0.0 - 1.0].
    """
    q = query.lower()

    # Match patterns like "score >= 85", "score > 80%", "score >= 0.85"
    m = re.search(r"score\s*(?:>=|>|:=|=|is|above|higher than|greater than|at least)\s*(\d+(?:\.\d+)?)\s*(%)?", q)
    if m:
        val = float(m.group(1))
        is_pct = m.group(2) == "%" or val > 1.0
        return (val / 100.0) if is_pct else val

    # Match standalone ">= 85", "> 90%"
    m2 = re.search(r"(?:>=|>)\s*(\d+(?:\.\d+)?)\s*(%)?", q)
    if m2:
        val = float(m2.group(1))
        is_pct = m2.group(2) == "%" or val > 1.0
        return (val / 100.0) if is_pct else val

    return None

def _is_explicit_search_intent(query: str) -> bool:
    """
    Checks if user is explicitly asking to search for a new domain / topic.
    """
    q = query.lower()
    triggers = ["search for ", "find ", "look for ", "search ", "load documents for ", "fetch documents "]
    return any(q.startswith(t) or f" {t}" in q for t in triggers)

def _extract_attached_filenames(query: str) -> List[str]:
    m = re.search(r"\[Attached Context Files:\s*(.*?)\]", query)
    if m:
        names = [n.strip() for n in m.group(1).split(",") if n.strip()]
        return names
    return []

async def _fetch_attached_documents_results(
    filenames: List[str],
    tenant_id: UUID,
    db: AsyncSession
) -> List[SearchResult]:
    if not filenames:
        return []

    import asyncio
    from sqlalchemy import select, text
    from app.models.document import Document
    from app.services.storage_service import generate_presigned_url

    results: List[SearchResult] = []
    for name in filenames:
        stmt = (
            select(Document)
            .where(Document.tenant_id == tenant_id, Document.title == name, Document.is_trashed == False)
            .order_by(Document.created_at.desc())
        )
        res = await db.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            continue

        chunk_sql = text("""
            SELECT c.id, c.content, c.page_number, c.chunk_index, d.title, d.id as doc_id, v.s3_path
            FROM doc_dg_chunks c
            JOIN doc_dg_documents d ON c.document_id = d.id
            LEFT JOIN doc_dg_document_versions v ON v.id = d.current_version_id
            WHERE d.id = :doc_id AND d.tenant_id = :tenant_id AND d.is_trashed = false
            ORDER BY c.page_number ASC, c.chunk_index ASC
            LIMIT 10
        """)

        rows = []
        for attempt in range(4):
            chunk_res = await db.execute(chunk_sql, {"doc_id": str(doc.id), "tenant_id": str(tenant_id)})
            rows = chunk_res.fetchall()
            if rows:
                break
            await asyncio.sleep(1.5)

        download_url = ""
        if rows and rows[0].s3_path:
            download_url = await generate_presigned_url(rows[0].s3_path)

        if rows:
            snippets = [r.content for r in rows[:4]]
            combined_snippet = "\n\n".join(snippets)
            if len(combined_snippet) > 1200:
                combined_snippet = combined_snippet[:1200] + "..."

            results.append(SearchResult(
                document_id=str(doc.id),
                document_name=doc.title,
                download_url=download_url,
                page_number=rows[0].page_number or 1,
                snippet=combined_snippet,
                score=1.0,
                tags=["attached"],
                metadata={"status": doc.status, "attached": True}
            ))
        else:
            results.append(SearchResult(
                document_id=str(doc.id),
                document_name=doc.title,
                download_url="",
                page_number=1,
                snippet=f"[Note: Extracted text for {doc.title} is currently being processed. Please ask again in a moment.]",
                score=1.0,
                tags=["attached"],
                metadata={"status": doc.status, "attached": True}
            ))

    return results

async def send_chat_message(
    session_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    query: str,
    db: AsyncSession,
    explicit_filters: Optional[dict] = None,
    ip_address: Optional[str] = None
) -> ChatMessage:

    session = await get_chat_session(session_id, tenant_id, user_id, db)
    if not session:
        raise ValueError("Chat session not found.")

    # 1. Fetch previous active documents (from latest assistant message with results)
    active_results: List[SearchResult] = []
    for msg in reversed(session.messages):
        if msg.role == "assistant" and msg.results:
            try:
                active_results = [SearchResult(**item) for item in msg.results]
                break
            except Exception:
                pass

    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=query,
        filters=explicit_filters
    )
    db.add(user_msg)

    # Auto-generate title if default
    if session.title == "New Persistent Chat":
        words = query.strip().split()
        new_title = " ".join(words[:5]).capitalize()
        if len(new_title) > 40:
            new_title = new_title[:37] + "..."
        session.title = new_title

    # Extract any explicitly attached files in query text
    attached_filenames = _extract_attached_filenames(query)
    attached_results: List[SearchResult] = []
    if attached_filenames:
        attached_results = await _fetch_attached_documents_results(attached_filenames, tenant_id, db)

    # 2. Determine processing mode
    score_threshold = _extract_score_threshold(query)
    is_search_intent = _is_explicit_search_intent(query) or len(active_results) == 0

    final_results: List[SearchResult] = []
    response_markdown = ""

    if is_search_intent and not attached_results and not (score_threshold is not None and len(active_results) > 0):
        # Fresh multi-domain hybrid search
        search_res: SearchResponse = await do_search(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            limit=10,
            filters=explicit_filters,
            db=db,
            ip_address=ip_address
        )
        final_results = search_res.results
        response_markdown = search_res.ai_summary

    else:
        # Operating on ALREADY LOADED LISTED FILES + ATTACHED DOCUMENTS
        existing_doc_ids = set()
        merged_list: List[SearchResult] = []

        # Attached files get highest priority at the top of loaded context
        for r in attached_results:
            merged_list.append(r)
            existing_doc_ids.add(r.document_id)

        # Include previously active session documents
        for r in active_results:
            if r.document_id not in existing_doc_ids:
                merged_list.append(r)
                existing_doc_ids.add(r.document_id)

        # Apply score filtering if requested
        if score_threshold is not None:
            merged_list = [r for r in merged_list if r.score >= score_threshold]

        # Apply dynamic sorting if requested
        if "sort by score" in query.lower() or "highest score" in query.lower() or "best match" in query.lower():
            merged_list = sorted(merged_list, key=lambda x: x.score, reverse=True)

        final_results = merged_list

        # Synthesize strictly grounded response strictly using listed files
        llm = get_llm_provider()
        
        if not final_results:
            response_markdown = f"No documents in the active listed files match your criteria (e.g. score >= {int((score_threshold or 0)*100)}%)."
        else:
            excerpts = []
            for idx, r in enumerate(final_results, 1):
                meta_str = ", ".join([f"{k}: {v}" for k, v in r.metadata.items()]) if r.metadata else "None"
                excerpts.append(
                    f"Document #{idx}: {r.document_name} (Page {r.page_number or 1}, Score: {int(r.score*100)}%)\n"
                    f"Metadata: {meta_str}\n"
                    f"Content Excerpt:\n{r.snippet}"
                )

            sys_prompt = (
                "You are an enterprise document intelligence assistant for a persistent chat thread.\n"
                "CRITICAL RULE: Answer the user's question accurately using ONLY the listed document excerpts below.\n"
                "- Do NOT invent details outside these listed documents.\n"
                "- Clearly reference document names, pages, scores, or metadata where relevant.\n"
                "- Organize your answer with clear headers, bold text, or bullet points."
            )

            context_block = "\n\n---\n\n".join(excerpts)
            user_prompt = f"User Request: {query}\n\nListed Documents Context:\n{context_block}"

            conversation_msgs = [Message(role="system", content=sys_prompt)]
            
            # Include recent 4 messages for dialogue context
            recent_msgs = session.messages[-4:]
            for m in recent_msgs:
                conversation_msgs.append(Message(role=m.role, content=m.content))

            conversation_msgs.append(Message(role="user", content=user_prompt))

            response_markdown = await llm.complete(conversation_msgs)

    # Convert results to jsonable dict list for storage (serializing UUIDs to strings)
    results_json = [json.loads(r.model_dump_json()) for r in final_results] if final_results else []
    filters_json = json.loads(json.dumps(explicit_filters, default=str)) if explicit_filters else None

    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response_markdown,
        results=results_json,
        filters=filters_json
    )
    db.add(assistant_msg)

    # Touch session timestamp
    session.updated_at = func.now()

    await db.commit()
    await db.refresh(assistant_msg)

    await log_action(
        db, user_id, tenant_id, "chat.message",
        details={"session_id": str(session_id), "query": query, "result_count": len(final_results)},
        ip_address=ip_address
    )

    return assistant_msg
