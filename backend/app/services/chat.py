"""
TextChatService — the Ollama-backed text chat channel.

All profile loading, prompt construction, and conversation memory is
delegated to DigitalTwinEngine (shared with VoiceChatService). This class
only owns what's specific to a text/HTTP request-response chat: an
in-memory session map and the actual Ollama call.
"""

from __future__ import annotations

from typing import Dict

from app.adapters import ollama_adapter
from app.services.ollama_client import OllamaClient
from app.services.twin_engine import DigitalTwinEngine, SessionNotFoundError


class TextChatService:
    def __init__(self, engine: DigitalTwinEngine | None = None):
        self.engine = engine or DigitalTwinEngine()
        self.client = OllamaClient()
        self.sessions: Dict[str, dict] = {}

    # ============================================================
    # Session Management
    # ============================================================

    def create_session(self, session_id: str, profile_id: str) -> str:
        context = self.engine.build_twin_context(profile_id)
        system_messages = ollama_adapter.build_messages(context)
        history = self.engine.load_history(profile_id)

        self.sessions[session_id] = {
            "profile_id": profile_id,
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

        session["history"] = self.engine.append_message(profile_id, "user", message, channel="text")

        dynamic_context = self.engine.build_dynamic_context(
            self.engine.get_recent_user_messages(session["history"])
        )

        messages = self.engine.build_context_window(
            session["system_messages"],
            session["history"],
            dynamic_context=dynamic_context,
        )

        reply = self.client.chat(messages, temperature=0.6, max_tokens=60)

        session["history"] = self.engine.append_message(profile_id, "assistant", reply, channel="text")

        return {"reply": reply}

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
        return {"summary": "Conversation summarization will be added in the next version."}
