import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from app.services.ollama_client import OllamaClient

MAX_HISTORY = 20
PROFILE_FILE = Path("personality.json")

class TwinChat:
    def __init__(self):
        self.client = OllamaClient()
        self.sessions = {}

    def load_profile(self, profile_id):
        profile_file = Path("profiles") / profile_id / "profile.json"
        if not profile_file.exists():
            raise FileNotFoundError(f"No personality profile found for profile ID: {profile_id}")
        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            raise FileNotFoundError("Personality profile is empty or invalid.")

    def build_system_prompt(self, profile):
        favorite_words = ", ".join(profile.get("favorite_words", []))
        values = ", ".join(profile.get("values", []))
        preferred_topics = ", ".join(profile.get("preferred_topics", []))

        prompt = f"""
You are the AI Digital Twin of the user.
Your goal is to communicate in a way that strongly reflects them.
Follow these personality traits and keep them consistent.

Tone: {profile.get("tone","")}
Communication Style: {profile.get("communication_style","")}
Favorite Words: {favorite_words}
Sentence Length: {profile.get("sentence_length","")}
Response Length: {profile.get("response_length","")}
Humor: {profile.get("humor","")}
Confidence: {profile.get("confidence","")}
Emotion: {profile.get("emotion","")}
Openness: {profile.get("openness","")}
Directness: {profile.get("directness","")}
Energy: {profile.get("energy","")}
Storytelling Style: {profile.get("storytelling_style","")}
Values: {values}
Preferred Topics: {preferred_topics}
Summary: {profile.get("summary","")}

Rules:
- Speak naturally.
- Don't mention you are AI.
- Don't mention personality analysis.
- Match the user's communication style.
- Use similar vocabulary.
- Keep responses consistent.
- Mirror their level of detail, energy, and directness.
- Prefer their preferred topics when it fits the conversation.
"""
        return prompt

    def get_initial_messages(self, profile) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": self.build_system_prompt(profile)
            }
        ]

    # ============================================================
    # Session Management
    # ============================================================

    def create_session(self, session_id, profile_id):
        profile = self.load_profile(profile_id)
        
        # Load conversation history from default.json if it exists
        messages = []
        conv_file = Path("profiles") / profile_id / "conversations" / "default.json"
        if conv_file.exists():
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    conv_data = json.load(f)
                    messages = conv_data.get("messages", [])
            except Exception:
                pass
        
        # If history is empty, initialize with system prompt
        if not messages:
            messages = self.get_initial_messages(profile)
            
        self.sessions[session_id] = {
            "profile": profile,
            "profile_id": profile_id,
            "messages": messages
        }
        
        # Update last_used in metadata.json
        meta_file = Path("profiles") / profile_id / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                meta_data["last_used"] = datetime.now().isoformat()
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, indent=4, ensure_ascii=False)
            except Exception:
                pass
                
        return session_id

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def session_exists(self, session_id):
        return session_id in self.sessions

    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

    # ============================================================
    # Chat Actions
    # ============================================================

    def receive_message(
        self,
        session_id,
        message
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Invalid session id")
        session["messages"].append(
            {
                "role": "user",
                "content": message
            }
        )
        
        # Save user message to persistent default.json
        profile_id = session.get("profile_id")
        if profile_id:
            conv_file = Path("profiles") / profile_id / "conversations" / "default.json"
            try:
                conv_file.parent.mkdir(parents=True, exist_ok=True)
                with open(conv_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {"messages": session["messages"]},
                        f,
                        indent=4,
                        ensure_ascii=False
                    )
            except Exception:
                pass

    def generate_reply(
        self,
        session_id
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Invalid session id")
        
        dynamic_context = self.build_dynamic_context(session_id)

        # Build messages using the context window to keep history capped
        messages = self.build_context_window(session_id)

        # Insert dynamic context as a system instruction after the main system prompt
        messages.insert(
            1,
            {
                "role": "system",
                "content": dynamic_context
            }
        )

        reply = self.client.chat(
            messages,
            temperature=0.7
        )

        session["messages"].append(
            {
                "role": "assistant",
                "content": reply
            }
        )

        # Save assistant message to persistent default.json
        profile_id = session.get("profile_id")
        if profile_id:
            conv_file = Path("profiles") / profile_id / "conversations" / "default.json"
            try:
                conv_file.parent.mkdir(parents=True, exist_ok=True)
                with open(conv_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {"messages": session["messages"]},
                        f,
                        indent=4,
                        ensure_ascii=False
                    )
            except Exception:
                pass

        return reply

    def chat(
        self,
        session_id,
        message
    ):
        self.receive_message(session_id, message)
        reply = self.generate_reply(session_id)
        return {
            "reply": reply
        }

    def export_chat(
        self,
        session_id
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Invalid session id")
        return session["messages"]

    # ============================================================
    # Recent User Messages
    # ============================================================

    def get_recent_user_messages(
        self,
        session_id,
        limit=5
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Invalid session id")
        messages = []
        for message in reversed(session["messages"]):
            if message["role"] == "user":
                messages.append(message["content"])
            if len(messages) >= limit:
                break
        messages.reverse()
        return messages

    # ============================================================
    # Dynamic Context
    # ============================================================

    def build_dynamic_context(
        self,
        session_id
    ):
        recent_messages = self.get_recent_user_messages(session_id)
        history = "\n".join(recent_messages)

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

    # ============================================================
    # Conversation Window
    # ============================================================

    def build_context_window(
        self,
        session_id
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Invalid session id")
        system_prompt = session["messages"][0]
        conversation = session["messages"][1:]

        if len(conversation) > MAX_HISTORY:
            conversation = conversation[-MAX_HISTORY:]

        return [
            system_prompt,
            *conversation
        ]

    # ============================================================
    # Memory Statistics
    # ============================================================

    def conversation_stats(
        self,
        session_id
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Invalid session id")
        total_user = 0
        total_ai = 0

        for message in session["messages"]:
            if message["role"] == "user":
                total_user += 1
            elif message["role"] == "assistant":
                total_ai += 1

        return {
            "total_messages": len(session["messages"]),
            "user_messages": total_user,
            "assistant_messages": total_ai
        }

    # ============================================================
    # Conversation Summary
    # ============================================================

    def summarize_conversation(
        self,
        session_id
    ):
        return {
            "summary": "Conversation summarization will be added in the next version."
        }
