from app.services.twin_engine import DigitalTwinEngine


def test_build_context_window_without_memory_context_is_unchanged():
    """Guards the "don't break existing functionality" requirement: a
    caller that never passes memory_context (every pre-RAG call site)
    must get byte-for-byte the same message list as before RAG existed."""
    engine = DigitalTwinEngine()
    system_messages = [{"role": "system", "content": "identity"}]
    history = [{"role": "user", "content": "hi", "channel": "text"}]

    with_default = engine.build_context_window(system_messages, history, dynamic_context="mood", summary="a summary")
    explicit_none = engine.build_context_window(
        system_messages, history, dynamic_context="mood", summary="a summary", memory_context=None
    )

    assert with_default == explicit_none
    assert not any("RELEVANT MEMORIES" in m["content"] for m in with_default)


def test_build_context_window_injects_memory_context_between_summary_and_dynamic_context():
    engine = DigitalTwinEngine()
    system_messages = [{"role": "system", "content": "identity"}]
    history = []

    messages = engine.build_context_window(
        system_messages,
        history,
        dynamic_context="DYNAMIC_MARKER",
        summary="SUMMARY_MARKER",
        memory_context="MEMORY_MARKER",
    )

    contents = [m["content"] for m in messages]
    assert "MEMORY_MARKER" in contents
    summary_idx = next(i for i, c in enumerate(contents) if "SUMMARY_MARKER" in c)
    memory_idx = next(i for i, c in enumerate(contents) if "MEMORY_MARKER" in c)
    dynamic_idx = next(i for i, c in enumerate(contents) if "DYNAMIC_MARKER" in c)
    assert summary_idx < memory_idx < dynamic_idx


def test_build_context_window_omits_memory_block_when_none():
    engine = DigitalTwinEngine()
    messages = engine.build_context_window([{"role": "system", "content": "id"}], [], memory_context=None)
    assert len(messages) == 1
