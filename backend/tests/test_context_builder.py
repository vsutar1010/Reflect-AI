from app.services.rag import context_builder
from app.services.rag.models import MemoryHit


def make_hit(content: str, source_type: str = "interview", score: float = 0.5) -> MemoryHit:
    return MemoryHit(content=content, source_type=source_type, source_id="0", timestamp="", score=score)


def test_build_memory_context_returns_none_for_empty_hits():
    assert context_builder.build_memory_context([]) is None


def test_build_memory_context_includes_all_hits_within_budget():
    hits = [make_hit("first memory"), make_hit("second memory", source_type="whatsapp")]
    block = context_builder.build_memory_context(hits, char_budget=1000)
    assert block is not None
    assert "first memory" in block
    assert "second memory" in block


def test_build_memory_context_instructs_llm_not_to_reveal_retrieval():
    # The block is a system-message instruction to the LLM, not the
    # user-facing reply itself — it must explicitly tell the model not
    # to mention searching/memory lookups, not merely avoid the phrase.
    hits = [make_hit("some fact about the user")]
    block = context_builder.build_memory_context(hits, char_budget=1000)
    lowered = block.lower()
    assert "never say" in lowered
    assert "searched" in lowered


def test_build_memory_context_respects_char_budget():
    hits = [make_hit("a" * 100), make_hit("b" * 100), make_hit("c" * 100)]
    block = context_builder.build_memory_context(hits, char_budget=150)
    # At least the first hit must be included, and the block must not
    # balloon past a couple of hits given the tight budget.
    assert "a" * 100 in block
    assert "c" * 100 not in block


def test_build_memory_context_always_includes_first_hit_even_if_over_budget():
    # A single very long hit shouldn't be dropped entirely just because
    # it alone exceeds the budget — some context beats none.
    hits = [make_hit("x" * 5000)]
    block = context_builder.build_memory_context(hits, char_budget=100)
    assert block is not None
    assert "x" * 5000 in block
