import pytest

from app.services.rag.memory_store import MemoryStore
from app.services.rag.models import MemoryRecord
from app.services.rag.retrieval_agent import RetrievalAgent
from tests.fakes import FakeEmbeddingProvider, FakeMongoCollection


def make_store_with(records, embedder):
    store = MemoryStore()
    store.collection = FakeMongoCollection()
    for r in records:
        r.embedding = embedder.embed_one(r.content)
        store.upsert(r)
    return store


class FixedLLMClient:
    """Stands in for OllamaClient in refine_query() tests — never makes
    a real network call."""

    def __init__(self, rewritten: str):
        self.rewritten = rewritten
        self.calls = 0

    def chat(self, messages, temperature=0.7, max_tokens=None, timeout=None):
        self.calls += 1
        return self.rewritten


class FailingLLMClient:
    def chat(self, *args, **kwargs):
        raise RuntimeError("LLM unavailable")


# ============================================================
# needs_retrieval() — the "skip retrieval for simple questions" gate
# ============================================================

@pytest.mark.parametrize("greeting", ["Hello", "hi!", "hey", "how are you?", "what's up", "thanks", "lol"])
def test_needs_retrieval_skips_small_talk(greeting):
    embedder = FakeEmbeddingProvider(vocab=["placeholder"])
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="placeholder")],
        embedder,
    )
    agent = RetrievalAgent(store, embedder)
    assert agent.needs_retrieval(greeting, "p1") is False


def test_needs_retrieval_true_for_substantive_question_with_memories():
    embedder = FakeEmbeddingProvider(vocab=["job", "work", "software", "engineer"])
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="job work")],
        embedder,
    )
    agent = RetrievalAgent(store, embedder)
    assert agent.needs_retrieval("What do I do for work?", "p1") is True


def test_needs_retrieval_false_when_profile_has_no_memories():
    embedder = FakeEmbeddingProvider(vocab=["job"])
    store = MemoryStore()
    store.collection = FakeMongoCollection()
    agent = RetrievalAgent(store, embedder)
    assert agent.needs_retrieval("What do I do for work, tell me about my career plans", "p1") is False


def test_needs_retrieval_true_for_memory_cue_even_if_short():
    embedder = FakeEmbeddingProvider(vocab=["x"])
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="x")],
        embedder,
    )
    agent = RetrievalAgent(store, embedder)
    assert agent.needs_retrieval("remember when we talked about this?", "p1") is True


# ============================================================
# retrieve() — the full bounded loop
# ============================================================

def test_retrieve_returns_relevant_memories_on_first_pass():
    embedder = FakeEmbeddingProvider(vocab=["pizza", "cheese", "favorite", "food"])
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="pizza cheese favorite food")],
        embedder,
    )
    agent = RetrievalAgent(store, embedder)

    result = agent.retrieve("u1", "p1", "what is my favorite food")

    assert result.used_retrieval is True
    assert len(result.memories) >= 1
    assert result.iterations == 1


def test_retrieve_skips_and_reports_unused_for_small_talk():
    embedder = FakeEmbeddingProvider(vocab=["x"])
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="x")],
        embedder,
    )
    agent = RetrievalAgent(store, embedder)

    result = agent.retrieve("u1", "p1", "hello")

    assert result.used_retrieval is False
    assert result.memories == []


def test_retrieve_never_exceeds_max_iterations(monkeypatch):
    embedder = FakeEmbeddingProvider(vocab=["completely", "unrelated", "vocabulary", "words", "here"])
    # Store has memories, but none share any vocabulary with the query,
    # so every iteration's evaluate() step comes back empty — this must
    # still terminate, not loop forever.
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="completely unrelated vocabulary")],
        embedder,
    )
    monkeypatch.setattr("app.config.RAG_MAX_ITERATIONS", 3)
    agent = RetrievalAgent(store, embedder, llm_client=FailingLLMClient())

    result = agent.retrieve("u1", "p1", "asking about something with zero overlap")

    assert result.used_retrieval is True
    assert result.iterations <= 3
    assert result.memories == []


def test_retrieve_uses_llm_refinement_when_provided_and_first_pass_insufficient(monkeypatch):
    embedder = FakeEmbeddingProvider(vocab=["career", "engineering", "job", "irrelevant"])
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="career engineering job")],
        embedder,
    )
    monkeypatch.setattr("app.config.RAG_MAX_ITERATIONS", 2)
    # Set an unreasonably high relevance bar so the first pass "fails"
    # and refinement is exercised.
    monkeypatch.setattr("app.config.RAG_MIN_RELEVANCE_SCORE", 2.0)
    llm = FixedLLMClient("career engineering job")
    agent = RetrievalAgent(store, embedder, llm_client=llm)

    result = agent.retrieve("u1", "p1", "irrelevant")

    assert llm.calls == 1
    assert result.iterations == 2


def test_retrieve_degrades_gracefully_when_embedding_fails():
    class BrokenEmbedder:
        name = "broken"

        def embed_one(self, text):
            raise RuntimeError("embedding service down")

    store = MemoryStore()
    store.collection = FakeMongoCollection()
    store.collection.update_one({"_id": "x"}, {"$set": {"_id": "x", "profile_id": "p1", "user_id": "u1", "source_type": "interview", "content": "c", "embedding": [1.0]}}, upsert=True)

    agent = RetrievalAgent(store, BrokenEmbedder())
    result = agent.retrieve("u1", "p1", "a substantive question about my life")

    assert result.used_retrieval is True
    assert result.memories == []


def test_retrieve_returns_unused_when_rag_disabled(monkeypatch):
    embedder = FakeEmbeddingProvider(vocab=["x"])
    store = make_store_with(
        [MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="x")],
        embedder,
    )
    monkeypatch.setattr("app.config.RAG_ENABLED", False)
    agent = RetrievalAgent(store, embedder)

    result = agent.retrieve("u1", "p1", "a substantive question here")

    assert result.used_retrieval is False
    assert result.reason == "rag_disabled"
