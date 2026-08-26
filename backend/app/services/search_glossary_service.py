"""TS7 — cross-script glossary-first search expansion.

Complements, not replaces, search_service.py's existing LLM-based
_expand_trilingual_query: that call already runs on every search
unconditionally and degrades to the raw query verbatim on any failure
(including air-gapped mode with no local LLM — enforce_local() blocks
it, and the except clause there just falls back to echoing the query).
This glossary is a free, local, always-available lookup for known
domain vocabulary that fills exactly that gap, and guarantees the exact
indexed term for known vocabulary rather than trusting a general-purpose
model's translation.

Deliberately narrow scope: only feeds the embedding leg of search
(search_service.py already searches each item in `tri_queries`
independently and RRF-merges — adding more query variants there is
purely additive). NOT folded into the keyword-search legs
(plainto_tsquery), which AND their terms together — concatenating extra
glossary words into q_en/q_mr would make keyword search MORE
restrictive, the opposite of expansion.
"""
import re
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_glossary import SearchGlossaryTerm

# Same Devanagari-aware word boundary as TS2's tokenizer (data_loss_audit.py):
# plain \w alone splits Devanagari words at combining-mark boundaries.
_WORD_RE = re.compile(r"[\wऀ-ॿ]+", re.UNICODE)


def _tokenize_words(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


async def expand_query_terms(db: AsyncSession, query: str) -> List[str]:
    """Returns extra cross-script synonym terms to add to the embedding
    leg's query variants — never the terms already present in the query
    itself. Best-effort: returns [] on any failure rather than breaking
    search."""
    try:
        words = _tokenize_words(query)
        if not words:
            return []

        candidates = set(words)
        for i in range(len(words) - 1):
            candidates.add(f"{words[i]} {words[i + 1]}")  # two-word glossary terms, e.g. "survey number"

        res = await db.execute(select(SearchGlossaryTerm).where(SearchGlossaryTerm.term.in_(candidates)))
        matched = res.scalars().all()
        if not matched:
            return []

        canonical_keys = {m.canonical_key for m in matched}
        group_res = await db.execute(
            select(SearchGlossaryTerm.term).where(SearchGlossaryTerm.canonical_key.in_(canonical_keys))
        )
        all_group_terms = {t for (t,) in group_res.all()}
        matched_terms = {m.term for m in matched}

        return sorted(all_group_terms - matched_terms)
    except Exception:
        return []
