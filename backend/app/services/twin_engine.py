"""
DigitalTwinEngine — the shared "brain" behind every digital twin.

This is the one place that knows how to:
  - load a profile and its source interview from MongoDB
  - turn that into a provider-agnostic TwinContext
  - read/write the twin's ongoing conversation memory
  - build a mood-adapting "dynamic context" from recent turns
  - assemble a final, context-window-capped message list ready for any LLM

It deliberately knows nothing about Ollama, Vapi, GPT-4o-mini, HTTP, or
FastAPI — it produces a TwinContext (see twin_context.py) and stops
there. Turning that into an Ollama message list or a Vapi system prompt
is a Prompt Adapter's job (see app/adapters/), not the engine's. That
separation is what lets Text Chat and Voice Chat use two entirely
different LLMs while still being provably the same personality: they
both start from the exact same TwinContext, built by the exact same
code, from the exact same profile and memory.

Storage: MongoDB, via app/database.py — a `profiles` collection (one
document per twin, _id = profile UUID) and a `conversations` collection
(one document per chat thread, _id = "{profile_id}:{thread}").
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from app.database import conversations_collection, profiles_collection
from app.services.twin_context import TwinContext

MAX_HISTORY = 20

# Word this person actually uses most for greetings (from communication
# stats) — used to build an instant, personality-flavored opening line
# without needing a slow LLM call just to say hello.
_GREETING_FALLBACK_ORDER = ["yo", "hey", "bro", "hi", "sup", "hello"]


class ProfileNotFoundError(FileNotFoundError):
    pass


class SessionNotFoundError(ValueError):
    pass


class DigitalTwinEngine:
    def __init__(self):
        # Small in-memory cache so we don't re-read profile.json and
        # conversation.json from disk on every single turn.
        # Keyed by profile_id -> TwinContext
        self._cache: Dict[str, TwinContext] = {}

    # ============================================================
    # Profile + Source Conversation Loading
    # ============================================================

    def load_profile(self, profile_id: str) -> dict:
        doc = profiles_collection.find_one({"_id": profile_id})
        if not doc or "profile" not in doc:
            raise ProfileNotFoundError(f"No personality profile found for profile ID: {profile_id}")
        return doc["profile"]

    def load_metadata(self, profile_id: str) -> dict:
        doc = profiles_collection.find_one({"_id": profile_id})
        if not doc:
            return {}
        return {
            "id": doc.get("_id"),
            "name": doc.get("name"),
            "created_at": doc.get("created_at"),
            "last_used": doc.get("last_used"),
            "version": doc.get("version"),
        }

    def load_source_conversation(self, profile_id: str) -> List[dict]:
        """
        The verbatim interview transcript captured during analysis
        (the profile document's `conversation` field) — the person's own raw
        words, distinct from `profile` (derived traits) and from the
        conversations collection (the twin's own ongoing chat log).
        """
        doc = profiles_collection.find_one({"_id": profile_id}, {"conversation": 1})
        if not doc:
            return []
        return doc.get("conversation", [])

    def get_voice_config(self, profile_id: str) -> Optional[dict]:
        """
        A profile's chosen Vapi voice (provider + voice_id + the gender
        preset it was picked from), set via PUT /api/profiles/{id}/voice.
        Returns None if the profile hasn't picked one yet — callers fall
        back to the global VAPI_VOICE_PROVIDER/VAPI_VOICE_ID default.
        """
        doc = profiles_collection.find_one({"_id": profile_id}, {"voice": 1})
        return doc.get("voice") if doc else None

    def touch_last_used(self, profile_id: str) -> None:
        try:
            profiles_collection.update_one(
                {"_id": profile_id},
                {"$set": {"last_used": datetime.now().isoformat()}},
            )
        except Exception:
            pass

    # ============================================================
    # TwinContext
    # ============================================================

    def _extract_voice_grounding_quotes(self, source_messages: List[dict], char_budget: int = 3000) -> List[str]:
        """
        Selects verbatim quotes from the person's real interview answers,
        most recent first, within a character budget. Returns a plain
        list — formatting these into an actual prompt block is an
        adapter's job, since how many quotes are worth including differs
        by how much a given model needs to see to sound authentic.
        """
        user_lines = [
            m.get("content", "").strip()
            for m in source_messages
            if m.get("role") == "user" and m.get("content", "").strip()
        ]

        if not user_lines:
            return []

        selected = []
        total = 0
        for line in reversed(user_lines):
            if selected and total + len(line) > char_budget:
                break
            selected.append(line)
            total += len(line)
        selected.reverse()

        return selected

    def build_twin_context(self, profile_id: str, force_reload: bool = False) -> TwinContext:
        """
        The provider-agnostic bundle every prompt adapter builds from.
        Cached per profile_id (invalidate with force_reload=True after
        regenerating a profile) so repeated turns don't re-read profile
        and conversation data from disk every time.
        """
        if not force_reload and profile_id in self._cache:
            return self._cache[profile_id]

        profile = self.load_profile(profile_id)
        source_conversation = self.load_source_conversation(profile_id)

        communication = profile.get("communication", {})
        llm_analysis = profile.get("llm_analysis", {})

        context = TwinContext(
            profile_id=profile_id,
            name=llm_analysis.get("name") or "",
            identity_prompt=profile.get("identity_prompt", ""),
            voice_grounding_quotes=self._extract_voice_grounding_quotes(source_conversation),
            personality=llm_analysis.get("personality", {}),
            thinking_pattern=llm_analysis.get("thinking_pattern", {}),
            emotional_style=llm_analysis.get("emotional_style", {}),
            conversation_behaviour=llm_analysis.get("conversation_behaviour", {}),
            interests=llm_analysis.get("interests", []),
            example_replies=llm_analysis.get("example_replies", []),
            summary=llm_analysis.get("summary", ""),
            favorite_words=communication.get("vocabulary", {}).get("favorite_words", []),
            emojis=list(communication.get("writing_style", {}).get("emoji_usage", {}).keys()),
            response_length=communication.get("conversation_style", {}).get("response_length", {}),
            greetings=communication.get("conversation_style", {}).get("greetings", {}),
        )

        self._cache[profile_id] = context
        return context

    def build_dynamic_context(self, recent_user_messages: List[str]) -> str:
        history = "\n".join(recent_user_messages)

        return f"""
The following are the user's MOST RECENT messages.

Analyze ONLY these messages.

Recent Messages

--------------------------

{history}

--------------------------

Update your behaviour accordingly.

Examples

If the user is excited
→ Become more energetic.

If the user is frustrated
→ Speak more seriously.

If the user is joking
→ Joke back.

If the user is asking technical questions
→ Become analytical.

Do NOT change the person's writing style.

Only adapt
- mood
- energy
- emotional expression
- conversation flow

while preserving the user's identity.
"""

    def build_opening_line(self, profile_id: str) -> str:
        """
        An instant, personality-flavored greeting built purely from
        already-computed communication stats — no LLM call, so it's
        available immediately (important for Voice Chat, where the
        assistant needs to say something the moment the call connects).
        """
        try:
            context = self.build_twin_context(profile_id)
        except ProfileNotFoundError:
            return "hey"

        greetings = context.greetings

        best_word = None
        best_count = 0
        for word, count in greetings.items():
            if count > best_count:
                best_word, best_count = word, count

        if not best_word:
            for word in _GREETING_FALLBACK_ORDER:
                if word in greetings:
                    best_word = word
                    break

        return best_word or "hey"

    # ============================================================
    # Conversation Memory
    # ============================================================
    # A single shared thread ("default") is used by both Text Chat and
    # Voice Chat by default, so switching channels mid-conversation feels
    # continuous rather than like talking to two different twins. Each
    # message is tagged with the channel it came from for UI display.

    def _thread_id(self, profile_id: str, thread: str) -> str:
        return f"{profile_id}:{thread}"

    def load_history(self, profile_id: str, thread: str = "default") -> List[dict]:
        doc = conversations_collection.find_one({"_id": self._thread_id(profile_id, thread)})
        if not doc:
            return []
        # Defensive: strip any legacy embedded system message from before
        # conversation memory was separated from prompts.
        return [m for m in doc.get("messages", []) if m.get("role") in ("user", "assistant")]

    def save_history(self, profile_id: str, messages: List[dict], thread: str = "default") -> None:
        try:
            conversations_collection.update_one(
                {"_id": self._thread_id(profile_id, thread)},
                {
                    "$set": {
                        "profile_id": profile_id,
                        "thread": thread,
                        "messages": messages,
                        "updated_at": datetime.now().isoformat(),
                    }
                },
                upsert=True,
            )
        except Exception:
            pass

    def append_message(
        self,
        profile_id: str,
        role: str,
        content: str,
        channel: str = "text",
        thread: str = "default",
    ) -> List[dict]:
        """Appends one turn to shared memory and persists it. Returns the full updated history."""
        history = self.load_history(profile_id, thread)
        history.append({"role": role, "content": content, "channel": channel})
        self.save_history(profile_id, history, thread)
        return history

    def get_recent_user_messages(self, history: List[dict], limit: int = 5) -> List[str]:
        messages = []
        for message in reversed(history):
            if message.get("role") == "user":
                messages.append(message.get("content", ""))
            if len(messages) >= limit:
                break
        messages.reverse()
        return messages

    def build_context_window(
        self,
        system_messages: List[Dict[str, str]],
        history: List[dict],
        dynamic_context: Optional[str] = None,
        max_history: int = MAX_HISTORY,
    ) -> List[Dict[str, str]]:
        """
        Assembles the final message list for an LLM call: persistent
        system messages (always kept, never dropped), then optionally a
        fresh dynamic-context system message, then the most recent turns
        of conversation (capped so token usage stays bounded).
        """
        conversation = history[-max_history:] if len(history) > max_history else history
        # Strip the "channel" tag before sending to an LLM — it's UI metadata.
        conversation = [{"role": m["role"], "content": m["content"]} for m in conversation]

        messages = list(system_messages)
        if dynamic_context:
            messages.append({"role": "system", "content": dynamic_context})
        messages.extend(conversation)
        return messages

    def invalidate_cache(self, profile_id: str) -> None:
        self._cache.pop(profile_id, None)
