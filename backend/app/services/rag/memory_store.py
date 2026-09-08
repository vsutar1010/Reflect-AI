"""
MemoryStore — MongoDB-backed storage and search for the `memories`
collection (see app/database.py).

Search prefers MongoDB Atlas Vector Search ($vectorSearch) when a
matching index exists, and transparently falls back to an in-process
brute-force cosine search otherwise — so retrieval works whether or not
backend/scripts/setup_memory_vector_index.py has been run, and whether
or not the underlying cluster tier even supports Atlas Search.

Every read/write here is scoped by BOTH profile_id and user_id, so a
bug in a calling layer can't leak one twin's or one user's memories
into another's context — the isolation is enforced at this boundary,
not just trusted from callers.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from pymongo.errors import PyMongoError

from app import config
from app.database import memories_collection
from app.services.rag.models import MemoryHit, MemoryRecord


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryStore:
    def __init__(self):
        self.collection = memories_collection

    # ============================================================
    # Writes
    # ============================================================

    def upsert(self, record: MemoryRecord) -> None:
        """Idempotent: re-indexing the same source_id overwrites in place
        rather than duplicating. Never raises — indexing is best-effort,
        matching the rest of this app's "never break the hot path"
        pattern (see TextChatService's summarization)."""
        try:
            doc = record.to_doc()
            self.collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        except PyMongoError:
            pass

    def upsert_many(self, records: List[MemoryRecord]) -> int:
        written = 0
        for record in records:
            try:
                doc = record.to_doc()
                self.collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
                written += 1
            except PyMongoError:
                continue
        return written

    def delete_profile_memories(self, profile_id: str) -> None:
        try:
            self.collection.delete_many({"profile_id": profile_id})
        except PyMongoError:
            pass

    def count_for_profile(self, profile_id: str) -> int:
        try:
            return self.collection.count_documents({"profile_id": profile_id})
        except PyMongoError:
            return 0

    # ============================================================
    # Search
    # ============================================================

    def search(
        self,
        user_id: str,
        profile_id: str,
        query_embedding: List[float],
        top_k: int,
        source_types: Optional[List[str]] = None,
    ) -> List[MemoryHit]:
        """
        Returns up to `top_k` memories scoped to (user_id, profile_id),
        ranked by relevance to `query_embedding`. Tries Atlas Vector
        Search first; falls back to a brute-force scan whenever vector
        search comes back with nothing — either because it raised
        (index missing, $vectorSearch unsupported on this cluster,
        transient error) OR because it ran successfully but returned
        zero hits. The empty-but-no-error case matters in practice: on
        at least some Atlas clusters, $vectorSearch against a
        *nonexistent* named index doesn't raise at all, it just returns
        no results — indistinguishable from "no index" and "genuinely
        no matches" without inspecting index metadata, so this method
        doesn't try to tell them apart and just always double-checks
        with brute force when vector search has nothing to show. Once a
        real index exists and is populated, the vector search branch
        returns non-empty results directly and brute force is never
        reached. Returns [] rather than raising on total failure —
        callers must treat empty results as "no memory context
        available", same as if RAG were off.
        """
        hits = self._vector_search(user_id, profile_id, query_embedding, top_k, source_types)
        if hits:
            return hits
        return self._brute_force_search(user_id, profile_id, query_embedding, top_k, source_types)

    def _vector_search(
        self,
        user_id: str,
        profile_id: str,
        query_embedding: List[float],
        top_k: int,
        source_types: Optional[List[str]],
    ) -> Optional[List[MemoryHit]]:
        match_filter: Dict[str, Any] = {"user_id": user_id, "profile_id": profile_id}
        if source_types:
            match_filter["source_type"] = {"$in": source_types}

        pipeline = [
            {
                "$vectorSearch": {
                    "index": config.MEMORY_VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": max(top_k * 20, 100),
                    "limit": top_k,
                    "filter": match_filter,
                }
            },
            {
                "$project": {
                    "content": 1,
                    "source_type": 1,
                    "source_id": 1,
                    "timestamp": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            results = list(self.collection.aggregate(pipeline))
        except PyMongoError:
            # Index not found / $vectorSearch unsupported on this
            # deployment / any other Mongo-side failure — the caller
            # falls back to brute-force search.
            return None

        return [MemoryHit.from_doc(doc, doc.get("score", 0.0)) for doc in results]

    def _brute_force_search(
        self,
        user_id: str,
        profile_id: str,
        query_embedding: List[float],
        top_k: int,
        source_types: Optional[List[str]],
    ) -> List[MemoryHit]:
        query: Dict[str, Any] = {"user_id": user_id, "profile_id": profile_id}
        if source_types:
            query["source_type"] = {"$in": source_types}

        try:
            cursor = self.collection.find(
                query,
                {"content": 1, "source_type": 1, "source_id": 1, "timestamp": 1, "metadata": 1, "embedding": 1},
            ).limit(config.RAG_BRUTE_FORCE_SCAN_LIMIT)
            docs = list(cursor)
        except PyMongoError:
            return []

        scored = []
        for doc in docs:
            embedding = doc.get("embedding")
            if not embedding:
                continue
            score = _cosine_similarity(query_embedding, embedding)
            scored.append((score, doc))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [MemoryHit.from_doc(doc, score) for score, doc in scored[:top_k]]
