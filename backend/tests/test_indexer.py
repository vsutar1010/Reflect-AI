from app.services.rag.indexer import MemoryIndexer, WHATSAPP_CHUNK_SIZE
from app.services.rag.memory_store import MemoryStore
from app.services.rag.models import SOURCE_CONVERSATION, SOURCE_INTERVIEW, SOURCE_WHATSAPP
from tests.fakes import FakeEmbeddingProvider, FakeMongoCollection


def make_indexer(vocab):
    store = MemoryStore()
    store.collection = FakeMongoCollection()
    embedder = FakeEmbeddingProvider(vocab=vocab)
    return MemoryIndexer(store, embedder), store


def test_index_interview_pairs_question_and_answer():
    indexer, store = make_indexer(["tell", "me", "about", "yourself", "i", "love", "hiking"])
    messages = [
        {"role": "assistant", "content": "tell me about yourself"},
        {"role": "user", "content": "i love hiking"},
    ]
    written = indexer.index_interview("p1", "u1", messages)

    assert written == 1
    doc = store.collection.find_one({"profile_id": "p1", "source_type": SOURCE_INTERVIEW})
    assert "tell me about yourself" in doc["content"]
    assert "i love hiking" in doc["content"]
    assert doc["embedding"] is not None


def test_index_interview_reindex_is_idempotent():
    indexer, store = make_indexer(["a"])
    messages = [{"role": "assistant", "content": "q"}, {"role": "user", "content": "a"}]
    indexer.index_interview("p1", "u1", messages)
    indexer.index_interview("p1", "u1", messages)
    assert store.count_for_profile("p1") == 1


def test_index_whatsapp_chunks_messages():
    indexer, store = make_indexer(["hey"])
    # More messages than one chunk, to verify chunking actually splits.
    messages = [{"role": "user", "content": f"message {i}"} for i in range(WHATSAPP_CHUNK_SIZE + 2)]
    indexer.index_whatsapp("p1", "u1", messages)

    count = store.count_for_profile("p1")
    assert count == 2  # one full chunk + one partial chunk
    for doc in store.collection.find({"profile_id": "p1", "source_type": SOURCE_WHATSAPP}):
        assert doc["embedding"] is not None


def test_index_conversation_turn_skips_trivial_messages():
    indexer, store = make_indexer(["hello"])
    indexer.index_conversation_turn("p1", "u1", "user", "ok", thread="default", turn_index=0)
    assert store.count_for_profile("p1") == 0  # too short, skipped


def test_index_conversation_turn_indexes_substantive_messages():
    indexer, store = make_indexer(["what", "is", "my", "favorite", "food"])
    indexer.index_conversation_turn("p1", "u1", "user", "what is my favorite food again", thread="default", turn_index=3)
    doc = store.collection.find_one({"profile_id": "p1", "source_type": SOURCE_CONVERSATION})
    assert doc is not None
    assert doc["metadata"]["role"] == "user"
    assert doc["metadata"]["thread"] == "default"


def test_index_conversation_summary_overwrites_in_place():
    indexer, store = make_indexer(["summary", "one", "two"])
    indexer.index_conversation_summary("p1", "u1", "summary one", thread="default")
    indexer.index_conversation_summary("p1", "u1", "summary two", thread="default")

    assert store.count_for_profile("p1") == 1
    doc = store.collection.find_one({"profile_id": "p1"})
    assert doc["content"] == "summary two"


def test_indexing_never_raises_when_embedding_fails():
    class BrokenEmbedder:
        name = "broken"

        def embed_many(self, texts):
            raise RuntimeError("embedding backend down")

        def embed_one(self, text):
            raise RuntimeError("embedding backend down")

    store = MemoryStore()
    store.collection = FakeMongoCollection()
    indexer = MemoryIndexer(store, BrokenEmbedder())

    # Must not raise — indexing failures are always best-effort.
    written = indexer.index_interview("p1", "u1", [{"role": "assistant", "content": "q"}, {"role": "user", "content": "a"}])
    assert written == 0
    assert store.count_for_profile("p1") == 0
