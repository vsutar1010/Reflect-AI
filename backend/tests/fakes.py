"""
Test doubles for the RAG layer.

Crucially, none of these ever touch the real `memories` collection on
the project's live MongoDB Atlas cluster — MemoryStore.collection is
swapped for FakeMongoCollection wherever a test needs storage behavior,
and embedding providers used in tests never make a real network call.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class FakeCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs

    def limit(self, n: int) -> "FakeCursor":
        return FakeCursor(self._docs[:n])

    def __iter__(self):
        return iter(self._docs)


class FakeMongoCollection:
    """A minimal in-memory stand-in for the subset of pymongo.Collection
    MemoryStore uses. aggregate() always raises, simulating "no Atlas
    Vector Search index" — the same fallback path production hits until
    scripts/setup_memory_vector_index.py has been run."""

    def __init__(self):
        self._docs: Dict[str, Dict[str, Any]] = {}

    def update_one(self, filt: dict, update: dict, upsert: bool = False):
        doc_id = filt["_id"]
        self._docs[doc_id] = dict(update["$set"])

    def find(self, query: dict, projection: Optional[dict] = None):
        results = [d for d in self._docs.values() if self._matches(d, query)]
        return FakeCursor(results)

    def find_one(self, query: dict, projection: Optional[dict] = None):
        for d in self._docs.values():
            if self._matches(d, query):
                return d
        return None

    def count_documents(self, query: dict) -> int:
        return sum(1 for d in self._docs.values() if self._matches(d, query))

    def delete_many(self, query: dict):
        to_delete = [k for k, d in self._docs.items() if self._matches(d, query)]
        for k in to_delete:
            del self._docs[k]

    def aggregate(self, pipeline: list):
        from pymongo.errors import PyMongoError

        raise PyMongoError("no Atlas Search index in this fake — forces brute-force fallback")

    @staticmethod
    def _matches(doc: dict, query: dict) -> bool:
        for key, value in query.items():
            if isinstance(value, dict) and "$in" in value:
                if doc.get(key) not in value["$in"]:
                    return False
            elif doc.get(key) != value:
                return False
        return True


class FakeEmbeddingProvider:
    """Deterministic fake: embeds text as a bag-of-words vector over a
    FIXED vocabulary supplied up front (unknown words are ignored), so
    every vector this instance produces has a stable, matching
    dimension — cosine similarity behaves predictably in tests without
    any real model or network call."""

    def __init__(self, vocab: List[str]):
        self.name = "fake"
        self.vocab = list(vocab)
        self.dimensions = len(self.vocab)

    def embed_one(self, text: str) -> List[float]:
        tokens = text.lower().split()
        vector = [0.0] * self.dimensions
        for t in tokens:
            if t in self.vocab:
                vector[self.vocab.index(t)] += 1.0
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector] if norm else vector

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_one(t) for t in texts]
