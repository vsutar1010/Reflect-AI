"""
Data shapes for the memory (RAG) layer.

Deliberately plain dataclasses — no pydantic/schema coupling to the API
layer, mirroring how TwinContext (app/services/twin_context.py) is kept
separate from the FastAPI schemas in app/schemas.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Kinds of historical data this layer can index. Every memory belongs to
# exactly one of these, recorded in `source_type` — used both to scope
# queries (e.g. only search WhatsApp history) and to label results back
# to the user-visible context block.
SOURCE_INTERVIEW = "interview"
SOURCE_WHATSAPP = "whatsapp"
SOURCE_CONVERSATION = "conversation"
SOURCE_CONVERSATION_SUMMARY = "conversation_summary"

VALID_SOURCE_TYPES = {
    SOURCE_INTERVIEW,
    SOURCE_WHATSAPP,
    SOURCE_CONVERSATION,
    SOURCE_CONVERSATION_SUMMARY,
}


@dataclass
class MemoryRecord:
    """One indexed chunk of a user's historical data, ready to embed/store."""

    user_id: str
    profile_id: str
    source_type: str
    # Stable, deterministic identifier for this chunk within its source
    # (e.g. "{profile_id}:interview:3") — used as the upsert key so
    # re-indexing never creates duplicates.
    source_id: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Populated by the embedding step, not at construction time.
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None

    def doc_id(self) -> str:
        return f"{self.profile_id}:{self.source_type}:{self.source_id}"

    def to_doc(self) -> Dict[str, Any]:
        return {
            "_id": self.doc_id(),
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "embedding_model": self.embedding_model,
            "updated_at": datetime.now().isoformat(),
        }


@dataclass
class MemoryHit:
    """A memory record returned from search, with its relevance score."""

    content: str
    source_type: str
    source_id: str
    timestamp: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_doc(cls, doc: Dict[str, Any], score: float) -> "MemoryHit":
        return cls(
            content=doc.get("content", ""),
            source_type=doc.get("source_type", ""),
            source_id=doc.get("source_id", ""),
            timestamp=doc.get("timestamp", ""),
            score=score,
            metadata=doc.get("metadata") or {},
        )


@dataclass
class RetrievalResult:
    """What the retrieval agent hands back to the caller."""

    used_retrieval: bool
    memories: List[MemoryHit] = field(default_factory=list)
    iterations: int = 0
    reason: str = ""  # short, non-sensitive note for server-side logs only
