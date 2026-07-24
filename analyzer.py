from __future__ import annotations

import json
import re
from pathlib import Path

from ollama_client import OllamaClient

PROFILE_FILE = Path("personality.json")
CONVERSATION_FILE = Path("conversations.json")


class PersonalityAnalyzer:

    def __init__(self):

        self.client = OllamaClient()
        self.messages = [
            {
                "role": "system",
                "content": """
You are ReflectAI, a natural conversation partner.

Your only job is to learn the user's personality by chatting in a relaxed, human way.

Rules:

- Do not sound like an interviewer or questionnaire.
- Do not ask generic prompt-like questions.
- Ask exactly one short question at a time.
- Base each question on what the user just said.
- Favor curiosity about habits, values, reactions, stories, preferences, and emotions.
- Avoid asking the same kind of question repeatedly.
- Do not explain that you are analyzing personality.
- Return only the question text.
"""
            }
        ]

    def save_conversation(self):

        with open(CONVERSATION_FILE, "w") as file_handle:
            json.dump(self.messages, file_handle, indent=4)

    def build_question_prompt(self):

        return [
            {
                "role": "system",
                "content": """
You are ReflectAI generating the next conversational question.

Write exactly one question that feels casual, specific, and human.

Rules:

- Base the question on the conversation so far.
- Do not use interview phrasing like 'tell me about yourself' or 'how would your friends describe you'.
- Avoid yes/no questions unless they naturally fit the context.
- Avoid generic, repeated, or template-style prompts.
- Keep it short enough to answer naturally.
- Return only the question text, with no preface, numbering, or explanation.
"""
            },
            *self.messages,
            {
                "role": "user",
                "content": "Ask the next natural question now."
            }
        ]

    def get_next_question(self):

        question = self.client.chat(
            self.build_question_prompt(),
            stream=False
        ).strip()

        question = re.sub(r"^\d+[).]\s*", "", question)
        question = question.strip('"').strip("'").replace("\n", " ").strip()

        if not question:
            question = "What has been on your mind lately?"

        if not question.endswith("?"):
            question = question.rstrip(".") + "?"

        return question

    def extract_profile_json(self, raw_text: str):

        cleaned = raw_text.strip()

        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fenced_match:
            try:
                return json.loads(fenced_match.group(1))
            except json.JSONDecodeError:
                pass

        start_index = cleaned.find("{")
        while start_index != -1:
            brace_depth = 0
            for index in range(start_index, len(cleaned)):
                char = cleaned[index]
                if char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth -= 1
                    if brace_depth == 0:
                        candidate = cleaned[start_index:index + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
            start_index = cleaned.find("{", start_index + 1)

        return None

    def generate_profile(self):

        print("\nGenerating Personality Profile...\n")

        analysis_prompt = self.messages.copy()
        analysis_prompt.append(
            {
                "role": "user",
                "content": """
Analyze the user's communication and personality from the full conversation.

Return ONLY valid JSON.

Use this schema:

{
    "tone": "",
    "communication_style": "",
    "favorite_words": [],
    "sentence_length": "",
    "response_length": "",
    "humor": "",
    "confidence": "",
    "emotion": "",
    "openness": "",
    "directness": "",
    "energy": "",
    "storytelling_style": "",
    "values": [],
    "preferred_topics": [],
    "summary": ""
}
"""
            }
        )

        profile = self.client.chat(
            analysis_prompt,
            stream=False
        )

        try:

            profile_json = self.extract_profile_json(profile)

            if profile_json is None:
                raise json.JSONDecodeError("No JSON object found", profile, 0)

            with open(PROFILE_FILE, "w") as file_handle:
                json.dump(profile_json, file_handle, indent=4)

            print("Personality profile saved.\n")

        except json.JSONDecodeError:

            print(profile)
            print("\nCouldn't parse JSON.\n")

    def run(self):

        print("=" * 50)
        print("ReflectAI Personality Analysis")
        print("=" * 50)
        print()
        print("Type /done when finished.\n")

        print("ReflectAI:")
        opening_question = "Let's talk naturally for a bit. What's been on your mind lately?"
        print(opening_question)

        self.messages.append(
            {
                "role": "assistant",
                "content": opening_question
            }
        )

        while True:

            user = input("\nYou : ").strip()

            if not user:
                continue

            if user.lower() == "/done":
                break

            self.messages.append(
                {
                    "role": "user",
                    "content": user
                }
            )

            next_question = self.get_next_question()

            self.messages.append(
                {
                    "role": "assistant",
                    "content": next_question
                }
            )

            print("\nReflectAI:")
            print(next_question)

        self.save_conversation()
        self.generate_profile()


if __name__ == "__main__":

    PersonalityAnalyzer().run()