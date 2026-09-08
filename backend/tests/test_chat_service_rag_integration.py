"""
Integration-style tests for the full "retrieval -> context builder ->
DigitalTwinEngine -> LLM" path inside TextChatService, using fakes for
the engine, LLM client, and RAG collaborators — no real network or
MongoDB access, so these are safe to run anywhere.
"""

from __future__ import annotations

from app.services.chat import TextChatService
from app.services.rag.models import MemoryHit, RetrievalResult


class FakeEngine:
    def __init__(self):
        self.history = []
        self.summary_state = {"summary": "", "summarized_through": 0}
        self.last_context_window_kwargs = None

    def append_message(self, profile_id, role, content, channel="text", thread="default"):
        self.history.append({"role": role, "content": content, "channel": channel})
        return list(self.history)

    def build_dynamic_context(self, recent_user_messages):
        return "DYNAMIC"

    def get_recent_user_messages(self, history, limit=5):
        return [m["content"] for m in history if m["role"] == "user"][-limit:]

    def get_summary_state(self, profile_id, thread="default"):
        return self.summary_state

    def save_summary_state(self, profile_id, summary, summarized_through, thread="default"):
        self.summary_state = {"summary": summary, "summarized_through": summarized_through}

    def build_context_window(self, system_messages, history, dynamic_context=None, summary=None, memory_context=None, max_history=20):
        self.last_context_window_kwargs = {
            "dynamic_context": dynamic_context,
            "summary": summary,
            "memory_context": memory_context,
        }
        return list(system_messages) + list(history)


class FakeOllamaClient:
    def __init__(self, reply="a reply"):
        self.reply = reply

    def chat(self, messages, temperature=0.7, max_tokens=None, timeout=None):
        return self.reply

    def stream_chat(self, messages, temperature=0.7, max_tokens=None):
        yield self.reply


class FakeRetrievalAgent:
    def __init__(self, result: RetrievalResult):
        self.result = result
        self.calls = []

    def retrieve(self, user_id, profile_id, query):
        self.calls.append((user_id, profile_id, query))
        return self.result


class FakeIndexer:
    def __init__(self):
        self.indexed_turns = []

    def index_conversation_turn(self, profile_id, user_id, role, content, thread, turn_index, channel="text"):
        self.indexed_turns.append((profile_id, user_id, role, content))

    def index_conversation_summary(self, profile_id, user_id, summary, thread="default"):
        pass


def make_service(retrieval_result=None, indexer=None):
    engine = FakeEngine()
    retrieval_agent = FakeRetrievalAgent(retrieval_result) if retrieval_result is not None else None
    service = TextChatService(engine=engine, memory_indexer=indexer, retrieval_agent=retrieval_agent)
    service.client = FakeOllamaClient()
    service.sessions["s1"] = {
        "profile_id": "p1",
        "owner_id": "u1",
        "system_messages": [{"role": "system", "content": "identity"}],
        "history": [],
    }
    return service, engine, retrieval_agent


def test_chat_without_rag_configured_behaves_like_before():
    service, engine, _ = make_service()
    result = service.chat("s1", "hello there")
    assert result == {"reply": "a reply"}
    assert engine.last_context_window_kwargs["memory_context"] is None


def test_chat_injects_retrieved_memory_context():
    hits = [MemoryHit(content="the user's favorite food is pizza", source_type="interview", source_id="0", timestamp="", score=0.9)]
    result_obj = RetrievalResult(used_retrieval=True, memories=hits, iterations=1)
    indexer = FakeIndexer()
    service, engine, agent = make_service(retrieval_result=result_obj, indexer=indexer)

    service.chat("s1", "what's my favorite food?")

    assert agent.calls == [("u1", "p1", "what's my favorite food?")]
    memory_context = engine.last_context_window_kwargs["memory_context"]
    assert memory_context is not None
    assert "pizza" in memory_context


def test_chat_falls_back_when_retrieval_returns_nothing():
    result_obj = RetrievalResult(used_retrieval=True, memories=[], iterations=2)
    service, engine, agent = make_service(retrieval_result=result_obj)

    service.chat("s1", "some question")

    assert engine.last_context_window_kwargs["memory_context"] is None


def test_chat_falls_back_when_retrieval_agent_raises():
    class BrokenAgent:
        def retrieve(self, *args, **kwargs):
            raise RuntimeError("mongo is down")

    engine = FakeEngine()
    service = TextChatService(engine=engine, retrieval_agent=BrokenAgent())
    service.client = FakeOllamaClient()
    service.sessions["s1"] = {
        "profile_id": "p1",
        "owner_id": "u1",
        "system_messages": [{"role": "system", "content": "identity"}],
        "history": [],
    }

    # Must not raise — a broken retrieval agent degrades to no memory
    # context, never breaks the chat turn itself.
    result = service.chat("s1", "some question")
    assert result == {"reply": "a reply"}
    assert engine.last_context_window_kwargs["memory_context"] is None


def test_chat_indexes_user_and_assistant_turns_when_indexer_configured():
    indexer = FakeIndexer()
    service, engine, _ = make_service(indexer=indexer)

    service.chat("s1", "a long enough user message to be indexed")

    roles_indexed = [t[2] for t in indexer.indexed_turns]
    assert "user" in roles_indexed
    assert "assistant" in roles_indexed


def test_stream_chat_also_injects_memory_context():
    hits = [MemoryHit(content="lives in Seattle", source_type="conversation", source_id="0", timestamp="", score=0.8)]
    result_obj = RetrievalResult(used_retrieval=True, memories=hits, iterations=1)
    service, engine, _ = make_service(retrieval_result=result_obj)

    tokens = list(service.stream_chat("s1", "where do I live?"))

    assert tokens == ["a reply"]
    memory_context = engine.last_context_window_kwargs["memory_context"]
    assert memory_context is not None
    assert "Seattle" in memory_context
