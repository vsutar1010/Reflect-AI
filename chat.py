from __future__ import annotations

import json
from pathlib import Path

from ollama_client import OllamaClient

PROFILE_FILE = Path("personality.json")


class TwinChat:

    def __init__(self):

        self.client = OllamaClient()

        if not PROFILE_FILE.exists():
            raise FileNotFoundError(
                "No personality profile found.\nRun Analyze Mode first."
            )

        try:
            with open(PROFILE_FILE, "r") as f:
                self.profile = json.load(f)
        except (json.JSONDecodeError, OSError):
            raise FileNotFoundError(
                "Personality profile is empty or invalid.\nRun Analyze Mode again."
            )

        self.messages = [
            {
                "role": "system",
                "content": self.build_system_prompt()
            }
        ]

    def build_system_prompt(self):

        favorite_words = ", ".join(self.profile.get("favorite_words", []))
        values = ", ".join(self.profile.get("values", []))
        preferred_topics = ", ".join(self.profile.get("preferred_topics", []))

        prompt = f"""
You are the AI Digital Twin of the user.

    Your goal is to communicate in a way that strongly reflects them.

    Follow these personality traits and keep them consistent.

Tone:
{self.profile.get("tone","")}

Communication Style:
{self.profile.get("communication_style","")}

Favorite Words:
{favorite_words}

Sentence Length:
{self.profile.get("sentence_length","")}

Response Length:
{self.profile.get("response_length","")}

Humor:
{self.profile.get("humor","")}

Confidence:
{self.profile.get("confidence","")}

Emotion:
{self.profile.get("emotion","")}

Openness:
{self.profile.get("openness","")}

Directness:
{self.profile.get("directness","")}

Energy:
{self.profile.get("energy","")}

Storytelling Style:
{self.profile.get("storytelling_style","")}

Values:
{values}

Preferred Topics:
{preferred_topics}

Summary:
{self.profile.get("summary","")}

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

    def run(self):

        print("=" * 50)
        print("ReflectAI Twin Chat")
        print("=" * 50)
        print()

        print("Type /exit to leave.\n")

        while True:

            user = input("You : ").strip()

            if not user:
                continue

            if user.lower() == "/exit":
                break

            self.messages.append(
                {
                    "role": "user",
                    "content": user
                }
            )

            print("\nTwin :", end=" ")

            reply = self.client.chat(self.messages)

            self.messages.append(
                {
                    "role": "assistant",
                    "content": reply
                }
            )

        print("\nGoodbye.")


if __name__ == "__main__":

    TwinChat().run()