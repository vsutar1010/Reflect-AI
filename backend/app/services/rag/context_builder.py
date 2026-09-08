"""
Formats retrieved memories into one system-message-shaped string,
budget-capped the same way twin_engine._extract_voice_grounding_quotes
budgets voice-grounding quotes — so RAG can never crowd the rest of the
context window out.

Returns None when there's nothing worth injecting, so callers can treat
"no memory context" identically to "RAG is off" (see TextChatService).
"""

from __future__ import annotations

from typing import List, Optional

from app import config
from app.services.rag.models import MemoryHit

_SOURCE_LABELS = {
    "interview": "from an earlier interview",
    "whatsapp": "from an imported WhatsApp history",
    "conversation": "from an earlier conversation",
    "conversation_summary": "conversation summary",
}


def build_memory_context(hits: List[MemoryHit], char_budget: int = config.RAG_MEMORY_CONTEXT_CHAR_BUDGET) -> Optional[str]:
    if not hits:
        return None

    lines = []
    total = 0
    for hit in hits:
        label = _SOURCE_LABELS.get(hit.source_type, hit.source_type)
        content = hit.content.strip().replace("\n", " ")
        line = f"- ({label}) {content}"
        if lines and total + len(line) > char_budget:
            break
        lines.append(line)
        total += len(line)

    if not lines:
        return None

    formatted = "\n".join(lines)

    return f"""
RELEVANT MEMORIES — snippets retrieved from this person's past interview
answers, imported chat history, or earlier conversations, because they
may be relevant to what was just asked:

{formatted}

Use these ONLY if they naturally help answer the current message. Treat
them as things you already know/remember, not as a document you were
shown. Never say "according to my memory", "I recall from our records",
or otherwise reveal that you searched anything — just answer naturally,
the way this person would if they simply remembered it.
"""
