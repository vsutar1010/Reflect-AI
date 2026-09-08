"""
TextChatService — the Ollama-backed text chat channel.

All profile loading, prompt construction, and conversation memory is
delegated to DigitalTwinEngine (shared with VoiceChatService). This class
only owns what's specific to a text/HTTP request-response chat: an
in-memory session map and the actual Ollama call.
"""

from __future__ import annotations

from typing import Dict, Iterator, List

from app.adapters import ollama_adapter
from app.services.ollama_client import OllamaClient
from app.services.rag import context_builder
from app.services.twin_engine import MAX_HISTORY, DigitalTwinEngine, SessionNotFoundError

# Below this many not-yet-summarized messages, skip the AI call rather than
# spend a round trip summarizing a single opening line — there's nothing
# worth compressing yet. Once a summary already exists, even one new
# message is folded in (it's cheap and keeps the summary from lagging).
MIN_MESSAGES_TO_SUMMARIZE = 2

_SUMMARY_SYSTEM_PROMPT = (
    "You compress a conversation into a short factual memory note. "
    "Preserve: facts the user stated about themselves, their preferences, "
    "decisions that were made, unresolved questions or tasks, and important "
    "topics discussed. Skip greetings, small talk, and filler. Write plain "
    "prose, under 120 words. If an existing summary is given, merge the new "
    "information into it and return ONE updated summary — never two "
    "separate summaries, never a list of the raw messages."
)


class TextChatService:
    def __init__(self, engine: DigitalTwinEngine | None = None, memory_indexer=None, retrieval_agent=None):
        self.engine = engine or DigitalTwinEngine()
        self.client = OllamaClient()
        self.sessions: Dict[str, dict] = {}
        # Both optional so this service still works (RAG simply
        # inactive) when constructed without them, e.g. in tests.
        self.memory_indexer = memory_indexer
        self.retrieval_agent = retrieval_agent

    # ============================================================
    # RAG — long-term memory (additive; any failure here falls back to
    # exactly the pre-RAG behavior of chat()/stream_chat())
    # ============================================================

    def _retrieve_memory_context(self, owner_id: str, profile_id: str, message: str) -> str | None:
        if self.retrieval_agent is None:
            return None
        try:
            result = self.retrieval_agent.retrieve(owner_id, profile_id, message)
            if not result.memories:
                return None
            return context_builder.build_memory_context(result.memories)
        except Exception as e:
            print(f"[rag] retrieval failed for profile {profile_id}, continuing without memory context: {e}")
            return None

    def _index_turn(self, owner_id: str, profile_id: str, role: str, content: str, history_len: int) -> None:
        if self.memory_indexer is None:
            return
        try:
            self.memory_indexer.index_conversation_turn(
                profile_id, owner_id, role, content, thread="default", turn_index=history_len - 1, channel="text"
            )
        except Exception as e:
            print(f"[rag] failed to index chat turn for profile {profile_id}: {e}")

    # ============================================================
    # Session Management
    # ============================================================

    def create_session(self, session_id: str, profile_id: str, owner_id: str) -> str:
        context = self.engine.build_twin_context(profile_id)
        system_messages = ollama_adapter.build_messages(context)
        history = self.engine.load_history(profile_id)

        self.sessions[session_id] = {
            "profile_id": profile_id,
            "owner_id": owner_id,
            "system_messages": system_messages,
            "history": history,
        }

        self.engine.touch_last_used(profile_id)

        return session_id

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def session_exists(self, session_id: str) -> bool:
        return session_id in self.sessions

    def delete_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def opening_line(self, profile_id: str) -> str:
        return self.engine.build_opening_line(profile_id)

    # ============================================================
    # Chat Actions
    # ============================================================

    def chat(self, session_id: str, message: str) -> dict:
        session = self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("Invalid session id")

        profile_id = session["profile_id"]
        owner_id = session["owner_id"]

        session["history"] = self.engine.append_message(profile_id, "user", message, channel="text")
        self._index_turn(owner_id, profile_id, "user", message, len(session["history"]))

        dynamic_context = self.engine.build_dynamic_context(
            self.engine.get_recent_user_messages(session["history"])
        )
        summary = self._catch_up_summary(profile_id, session["history"], owner_id=owner_id)
        memory_context = self._retrieve_memory_context(owner_id, profile_id, message)

        messages = self.engine.build_context_window(
            session["system_messages"],
            session["history"],
            dynamic_context=dynamic_context,
            summary=summary,
            memory_context=memory_context,
        )

        # Generous headroom: the current free-tier model spends a chunk
        # of this budget on hidden reasoning tokens before any actual
        # reply content, so a tight cap here risks getting back nothing.
        reply = self.client.chat(messages, temperature=0.6, max_tokens=700)

        session["history"] = self.engine.append_message(profile_id, "assistant", reply, channel="text")
        self._index_turn(owner_id, profile_id, "assistant", reply, len(session["history"]))

        return {"reply": reply}

    def stream_chat(self, session_id: str, message: str) -> Iterator[str]:
        """
        Same turn as chat() — same history append, same context window,
        same reply persisted to memory at the end — but yields the reply
        token-by-token as Ollama generates it, so the caller (the
        /api/chat/message SSE branch) can forward each token to the
        frontend as soon as it exists instead of waiting for the full
        reply. Mirrors VoiceChatService.stream_turn.
        """
        session = self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("Invalid session id")

        profile_id = session["profile_id"]
        owner_id = session["owner_id"]

        session["history"] = self.engine.append_message(profile_id, "user", message, channel="text")
        self._index_turn(owner_id, profile_id, "user", message, len(session["history"]))

        dynamic_context = self.engine.build_dynamic_context(
            self.engine.get_recent_user_messages(session["history"])
        )
        summary = self._catch_up_summary(profile_id, session["history"], owner_id=owner_id)
        memory_context = self._retrieve_memory_context(owner_id, profile_id, message)

        messages = self.engine.build_context_window(
            session["system_messages"],
            session["history"],
            dynamic_context=dynamic_context,
            summary=summary,
            memory_context=memory_context,
        )

        full_reply = []
        for token in self.client.stream_chat(messages, temperature=0.6, max_tokens=700):
            full_reply.append(token)
            yield token

        reply = "".join(full_reply)
        session["history"] = self.engine.append_message(profile_id, "assistant", reply, channel="text")
        self._index_turn(owner_id, profile_id, "assistant", reply, len(session["history"]))

    # ============================================================
    # Conversation Summarization
    # ============================================================
    # A single running summary per (profile_id, thread) — stored on the
    # same conversation document `messages` lives on (see
    # DigitalTwinEngine.get_summary_state/save_summary_state) — covering
    # `summarized_through` messages from the start of history. Two call
    # sites share this one mechanism:
    #   - _catch_up_summary(), called every turn from chat()/stream_chat(),
    #     folds in whatever has just scrolled outside build_context_window's
    #     max_history so that context isn't silently lost once a
    #     conversation runs long.
    #   - summarize_conversation(), an on-demand "summarize everything so
    #     far" action a caller can invoke directly.
    # Both funnel through _fold_into_summary(), so there is exactly one
    # summary per conversation, never two independent ones, and calling
    # either path again with nothing new to fold in is a no-op (no
    # duplicate AI call, no duplicate write).

    def _catch_up_summary(self, profile_id: str, history: List[dict], owner_id: str | None = None) -> str:
        """Keeps the stored summary caught up to everything that has fallen
        outside the recent context window, so far-back context is folded
        into the summary instead of being dropped forever."""
        upto = max(0, len(history) - MAX_HISTORY)
        return self._fold_into_summary(profile_id, history, upto, owner_id=owner_id)

    def _fold_into_summary(
        self, profile_id: str, history: List[dict], upto: int, thread: str = "default", owner_id: str | None = None
    ) -> str:
        """
        Ensures the stored summary covers `history[:upto]`, generating one
        AI call only for the messages not already covered. Never raises —
        any AI or MongoDB failure falls back to the last known-good
        summary (or "" if there isn't one yet) so a chat turn, or an
        explicit summarize request, is never broken by this failing.
        Existing `messages` history is never read from here in a way that
        could overwrite or lose it — only the separate summary fields are
        written.
        """
        state = self.engine.get_summary_state(profile_id, thread)
        existing_summary = state["summary"]
        already = state["summarized_through"]

        upto = max(0, min(upto, len(history)))
        if upto <= already:
            return existing_summary

        new_messages = history[already:upto]
        if not new_messages:
            return existing_summary
        if len(new_messages) < MIN_MESSAGES_TO_SUMMARIZE and not existing_summary:
            return existing_summary

        transcript = "\n".join(
            f"{m['role']}: {m['content']}" for m in new_messages if m.get("content", "").strip()
        )
        if not transcript.strip():
            return existing_summary

        prompt_messages = [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    (f"Existing summary:\n{existing_summary}\n\n" if existing_summary else "")
                    + f"New conversation to fold in:\n{transcript}\n\nUpdated summary:"
                ),
            },
        ]

        try:
            new_summary = self.client.chat(prompt_messages, temperature=0.3, max_tokens=700).strip()
        except Exception as e:
            # Covers Ollama being unreachable (RuntimeError from the
            # client) as well as any unexpected parsing failure — either
            # way, summarization is best-effort and must never break the
            # actual chat turn that triggered it.
            print(f"[chat] summarization failed for profile {profile_id}: {e}")
            return existing_summary

        if not new_summary:
            return existing_summary

        self.engine.save_summary_state(profile_id, new_summary, upto, thread)

        if self.memory_indexer is not None and owner_id is not None:
            try:
                self.memory_indexer.index_conversation_summary(profile_id, owner_id, new_summary, thread)
            except Exception as e:
                print(f"[rag] failed to index conversation summary for profile {profile_id}: {e}")

        return new_summary

    def export_chat(self, session_id: str):
        session = self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("Invalid session id")
        return session["history"]

    def conversation_stats(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("Invalid session id")

        history = session["history"]
        user_count = sum(1 for m in history if m["role"] == "user")
        assistant_count = sum(1 for m in history if m["role"] == "assistant")

        return {
            "total_messages": len(history),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
        }

    def summarize_conversation(self, session_id: str) -> dict:
        """
        On-demand "summarize everything so far" — folds the whole current
        history into the same running summary chat()/stream_chat() keep
        caught up incrementally (see _fold_into_summary), so calling this
        never produces a second, divergent summary. Calling it again with
        no new messages since the last summarization is a no-op: it
        returns the existing summary without another AI call.
        """
        session = self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("Invalid session id")

        profile_id = session["profile_id"]
        history = session["history"]

        if not history:
            return {"summary": "", "message": "No conversation yet to summarize."}

        summary = self._fold_into_summary(profile_id, history, len(history), owner_id=session.get("owner_id"))
        if not summary:
            return {"summary": "", "message": "Not enough conversation yet to summarize."}
        return {"summary": summary}
