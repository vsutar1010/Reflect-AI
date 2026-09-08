"""
MemoryIndexer — turns ReflectAI's existing historical data into
`memories` records, without ever modifying that original data.

Sources indexed:
  - interview   : the Q&A transcript captured at profile creation
                   (profiles.conversation, for interview-built profiles)
  - whatsapp    : the imported sender's own messages
                   (profiles.conversation, for WhatsApp-built profiles),
                   chunked so a huge import doesn't become one embedding
                   call per message
  - conversation: individual live chat turns (conversations.messages),
                   as they happen
  - conversation_summary: the running AI summary of a thread
                   (conversations.summary) — one memory doc per thread,
                   kept up to date in place (same doc_id) as the
                   summary evolves

All embedding + write calls are best-effort: any failure is logged and
swallowed so indexing can never break profile creation or a chat turn.
"""

from __future__ import annotations

from typing import Dict, List

from app.services.rag.embedding_service import EmbeddingError, EmbeddingProvider
from app.services.rag.memory_store import MemoryStore
from app.services.rag.models import (
    SOURCE_CONVERSATION,
    SOURCE_CONVERSATION_SUMMARY,
    SOURCE_INTERVIEW,
    SOURCE_WHATSAPP,
    MemoryRecord,
)

# How many consecutive WhatsApp messages get folded into one memory
# chunk. A multi-year export can be tens of thousands of one-line
# messages — embedding each individually would be both slow and a poor
# retrieval unit (a single "lol" carries no useful semantic content on
# its own). Interview answers don't need this: there are only ~10-20 of
# them and each is already a substantial, self-contained answer.
WHATSAPP_CHUNK_SIZE = 6

# Skip embedding a chat turn shorter than this — greetings/acks ("ok",
# "lol", "hey") add index noise without adding retrievable information.
MIN_CONVERSATION_TURN_CHARS = 12


class MemoryIndexer:
    def __init__(self, store: MemoryStore, embedding_provider: EmbeddingProvider):
        self.store = store
        self.embedder = embedding_provider

    def _embed_and_upsert(self, records: List[MemoryRecord]) -> int:
        if not records:
            return 0
        try:
            vectors = self.embedder.embed_many([r.content for r in records])
        except EmbeddingError as e:
            print(f"[rag] embedding failed during indexing ({len(records)} chunk(s)): {e}")
            return 0
        except Exception as e:  # defensive: never let indexing break a caller
            print(f"[rag] unexpected embedding failure during indexing: {e}")
            return 0

        for record, vector in zip(records, vectors):
            record.embedding = vector
            record.embedding_model = self.embedder.name

        return self.store.upsert_many(records)

    # ============================================================
    # Interview transcript
    # ============================================================

    def index_interview(self, profile_id: str, user_id: str, messages: List[Dict]) -> int:
        """
        `messages` is the profile's saved interview transcript:
        alternating {"role": "assistant", "content": <question>} /
        {"role": "user", "content": <answer>}. Each question+answer pair
        becomes one memory chunk — a more useful retrieval unit than
        either half alone.
        """
        records: List[MemoryRecord] = []
        pending_question = None
        pair_index = 0

        for msg in messages:
            role = msg.get("role")
            content = (msg.get("content") or "").strip()
            if not content:
                continue

            if role == "assistant":
                pending_question = content
            elif role == "user":
                if pending_question:
                    text = f"Q: {pending_question}\nA: {content}"
                else:
                    text = content
                records.append(
                    MemoryRecord(
                        user_id=user_id,
                        profile_id=profile_id,
                        source_type=SOURCE_INTERVIEW,
                        source_id=str(pair_index),
                        content=text,
                        metadata={"question": pending_question} if pending_question else {},
                    )
                )
                pair_index += 1
                pending_question = None

        return self._embed_and_upsert(records)

    # ============================================================
    # WhatsApp import
    # ============================================================

    def index_whatsapp(self, profile_id: str, user_id: str, messages: List[Dict]) -> int:
        """`messages` is the target sender's own texts, role="user" each
        (see WhatsAppParser.build_target_messages) — no counterpart
        messages, no timestamps preserved at this layer (the parser
        doesn't carry them through to the analysis pipeline)."""
        records: List[MemoryRecord] = []
        chunk_index = 0

        for start in range(0, len(messages), WHATSAPP_CHUNK_SIZE):
            chunk = messages[start : start + WHATSAPP_CHUNK_SIZE]
            texts = [(m.get("content") or "").strip() for m in chunk if (m.get("content") or "").strip()]
            if not texts:
                continue
            records.append(
                MemoryRecord(
                    user_id=user_id,
                    profile_id=profile_id,
                    source_type=SOURCE_WHATSAPP,
                    source_id=str(chunk_index),
                    content="\n".join(texts),
                    metadata={"message_count": len(texts)},
                )
            )
            chunk_index += 1

        return self._embed_and_upsert(records)

    # ============================================================
    # Live conversation (text + voice)
    # ============================================================

    def index_conversation_turn(
        self,
        profile_id: str,
        user_id: str,
        role: str,
        content: str,
        thread: str,
        turn_index: int,
        channel: str = "text",
    ) -> None:
        content = (content or "").strip()
        if len(content) < MIN_CONVERSATION_TURN_CHARS:
            return
        record = MemoryRecord(
            user_id=user_id,
            profile_id=profile_id,
            source_type=SOURCE_CONVERSATION,
            source_id=f"{thread}:{turn_index}",
            content=content,
            metadata={"role": role, "thread": thread, "channel": channel},
        )
        self._embed_and_upsert([record])

    def index_conversation_summary(self, profile_id: str, user_id: str, summary: str, thread: str = "default") -> None:
        """One memory doc per thread, overwritten in place as the
        summary evolves — never grows unbounded like per-turn indexing
        would."""
        summary = (summary or "").strip()
        if not summary:
            return
        record = MemoryRecord(
            user_id=user_id,
            profile_id=profile_id,
            source_type=SOURCE_CONVERSATION_SUMMARY,
            source_id=thread,
            content=summary,
            metadata={"thread": thread},
        )
        self._embed_and_upsert([record])


_indexer_singleton: MemoryIndexer | None = None


def get_indexer() -> MemoryIndexer:
    global _indexer_singleton
    if _indexer_singleton is None:
        from app.services.rag.embedding_service import get_embedding_provider

        _indexer_singleton = MemoryIndexer(MemoryStore(), get_embedding_provider())
    return _indexer_singleton
