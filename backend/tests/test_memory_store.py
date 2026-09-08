from app.services.rag.memory_store import MemoryStore
from app.services.rag.models import MemoryRecord
from tests.fakes import FakeEmbeddingProvider, FakeMongoCollection


def make_store() -> MemoryStore:
    store = MemoryStore()
    store.collection = FakeMongoCollection()
    return store


def test_upsert_is_idempotent_by_source_id():
    store = make_store()
    record = MemoryRecord(
        user_id="u1", profile_id="p1", source_type="interview", source_id="0",
        content="first version", embedding=[1.0, 0.0],
    )
    store.upsert(record)
    assert store.count_for_profile("p1") == 1

    record.content = "updated version"
    store.upsert(record)
    assert store.count_for_profile("p1") == 1  # overwritten, not duplicated

    doc = store.collection.find_one({"profile_id": "p1"})
    assert doc["content"] == "updated version"


def test_search_scopes_by_user_and_profile():
    store = make_store()
    embedder = FakeEmbeddingProvider(vocab=["pizza", "hiking", "mountains", "budget"])

    store.upsert(MemoryRecord(
        user_id="alice", profile_id="p1", source_type="interview", source_id="0",
        content="pizza", embedding=embedder.embed_one("pizza"),
    ))
    store.upsert(MemoryRecord(
        # Same content/profile_id, but a DIFFERENT user — must never be
        # returned for alice's search (cross-user isolation).
        user_id="bob", profile_id="p1", source_type="interview", source_id="1",
        content="pizza", embedding=embedder.embed_one("pizza"),
    ))
    store.upsert(MemoryRecord(
        # Same user, but a DIFFERENT profile (twin) — must not leak
        # across a user's own multiple twins either.
        user_id="alice", profile_id="p2", source_type="interview", source_id="0",
        content="pizza", embedding=embedder.embed_one("pizza"),
    ))

    hits = store.search("alice", "p1", embedder.embed_one("pizza"), top_k=10)
    assert len(hits) == 1
    assert hits[0].content == "pizza"


def test_search_ranks_by_relevance():
    store = make_store()
    embedder = FakeEmbeddingProvider(vocab=["pizza", "cheese", "hiking", "mountains", "unrelated", "topic"])

    store.upsert(MemoryRecord(
        user_id="u1", profile_id="p1", source_type="interview", source_id="0",
        content="pizza cheese", embedding=embedder.embed_one("pizza cheese"),
    ))
    store.upsert(MemoryRecord(
        user_id="u1", profile_id="p1", source_type="interview", source_id="1",
        content="hiking mountains", embedding=embedder.embed_one("hiking mountains"),
    ))
    store.upsert(MemoryRecord(
        user_id="u1", profile_id="p1", source_type="interview", source_id="2",
        content="unrelated topic", embedding=embedder.embed_one("unrelated topic"),
    ))

    hits = store.search("u1", "p1", embedder.embed_one("pizza cheese"), top_k=2)
    assert len(hits) == 2
    assert hits[0].content == "pizza cheese"
    assert hits[0].score > hits[1].score


def test_search_falls_back_to_brute_force_when_vector_search_raises():
    # FakeMongoCollection.aggregate() always raises — this asserts the
    # documented fallback behavior actually kicks in rather than
    # propagating the error or returning nothing.
    store = make_store()
    embedder = FakeEmbeddingProvider(vocab=["hello", "world"])
    store.upsert(MemoryRecord(
        user_id="u1", profile_id="p1", source_type="conversation", source_id="0",
        content="hello world", embedding=embedder.embed_one("hello world"),
    ))
    hits = store.search("u1", "p1", embedder.embed_one("hello world"), top_k=5)
    assert len(hits) == 1


def test_search_falls_back_to_brute_force_when_vector_search_returns_empty_without_error():
    # Regression test: on real Atlas, $vectorSearch against a named
    # index that simply doesn't exist yet was observed to return an
    # EMPTY result set rather than raising — before this was handled,
    # MemoryStore.search() treated `hits = []` as "vector search is
    # available and found nothing" and returned early, never trying
    # brute force, so retrieval silently found nothing until someone
    # manually ran scripts/setup_memory_vector_index.py. Simulates that
    # exact shape here: aggregate() succeeds (no exception) but yields
    # zero documents.
    store = make_store()
    store.collection.aggregate = lambda pipeline: iter([])  # succeeds, empty
    embedder = FakeEmbeddingProvider(vocab=["hello", "world"])
    store.upsert(MemoryRecord(
        user_id="u1", profile_id="p1", source_type="conversation", source_id="0",
        content="hello world", embedding=embedder.embed_one("hello world"),
    ))

    hits = store.search("u1", "p1", embedder.embed_one("hello world"), top_k=5)

    assert len(hits) == 1
    assert hits[0].content == "hello world"


def test_search_trusts_vector_search_when_it_returns_real_hits():
    # The counterpart to the two fallback tests above: once vector
    # search DOES return something, brute force must not silently
    # re-run and change the ranking/source of truth.
    store = make_store()
    brute_force_calls = []
    store._brute_force_search = lambda *a, **k: brute_force_calls.append(1) or []
    store.collection.aggregate = lambda pipeline: iter(
        [{"content": "from vector search", "source_type": "interview", "source_id": "0", "timestamp": "", "metadata": {}, "score": 0.9}]
    )

    hits = store.search("u1", "p1", [1.0, 0.0], top_k=5)

    assert len(hits) == 1
    assert hits[0].content == "from vector search"
    assert brute_force_calls == []


def test_delete_profile_memories_removes_only_that_profile():
    store = make_store()
    store.upsert(MemoryRecord(user_id="u1", profile_id="p1", source_type="interview", source_id="0", content="a", embedding=[1.0]))
    store.upsert(MemoryRecord(user_id="u1", profile_id="p2", source_type="interview", source_id="0", content="b", embedding=[1.0]))

    store.delete_profile_memories("p1")

    assert store.count_for_profile("p1") == 0
    assert store.count_for_profile("p2") == 1


def test_search_with_no_matching_documents_returns_empty_list():
    store = make_store()
    embedder = FakeEmbeddingProvider(vocab=["a", "b"])
    hits = store.search("nobody", "nothing", embedder.embed_one("a"), top_k=5)
    assert hits == []
