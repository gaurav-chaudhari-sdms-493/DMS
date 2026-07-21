from typing import List
from app.ai.base import LLMProvider, Message
import logging

logger = logging.getLogger(__name__)

class LocalLLMProvider(LLMProvider):
    """100% offline local LLM provider that synthesizes concise summaries directly from retrieved context."""

    def __init__(self, model_name: str = "local-synthesizer"):
        self.model_name = model_name

    async def complete(self, messages: List[Message], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        user_content = ""
        for m in messages:
            if m.role == "user":
                user_content = m.content

        if not user_content:
            return "No search results or context available."

        # Parse excerpts if present in prompt
        if "Excerpts:" in user_content:
            parts = user_content.split("Excerpts:\n", 1)
            excerpts_part = parts[1].strip()
            
            excerpts = [e.strip() for e in excerpts_part.split("\n---\n") if e.strip()]
            if not excerpts:
                return "No matching document details found in context."
                
            summary_lines = []
            summary_lines.append(f"Based on the top matching documents:")
            for idx, exc in enumerate(excerpts[:3], 1):
                lines = exc.split("\n")
                doc_title = lines[0] if lines else f"Document #{idx}"
                content = " ".join([l.strip() for l in lines[1:] if l.strip()])
                if len(content) > 250:
                    content = content[:247] + "..."
                summary_lines.append(f"• **{doc_title}**: {content}")

            return "\n".join(summary_lines)
            
        return user_content[:500]
