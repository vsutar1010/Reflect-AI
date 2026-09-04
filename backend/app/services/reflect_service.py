"""
ReflectService — AI-generated reflection/analysis for journal entries.

Journaling itself (create/list/get/update/delete) is plain MongoDB CRUD,
handled directly in app/routers/reflect.py (mirrors profiles.py, which
does the same for profile documents). This service owns only the one
piece that isn't plain CRUD: turning a journal entry's text into a
structured AI reflection, using the same OllamaClient every other AI
feature in this app already uses. It has no session/memory state of its
own — each entry is analyzed independently, from its own text only.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from app.services.ollama_client import OllamaClient

# A journal entry is one request/response, not a live conversation — cap
# the wait so a stalled Ollama call can't hang the request indefinitely.
ANALYSIS_TIMEOUT_SECONDS = 45

_ALLOWED_MOODS = {"Positive", "Negative", "Neutral", "Mixed"}
_MAX_THEMES = 5

_SYSTEM_PROMPT = (
    "You are a reflective journaling assistant, not a therapist or doctor. "
    "Never diagnose mental health conditions, never make medical claims, and "
    "never state the writer's emotions with false certainty — a short "
    "journal entry is limited evidence, so stay tentative and avoid "
    "judgmental language. Analyze ONLY the journal entry given below; do "
    "not invent facts that aren't in it. Keep 'observations' (patterns you "
    "notice) separate from 'reflection' (your interpretation) — don't "
    "blend the two.\n\n"
    "Respond with ONLY valid JSON (no markdown fences, no commentary before "
    "or after it), exactly this shape:\n"
    '{"mood": "Positive|Negative|Neutral|Mixed", '
    '"themes": ["short theme", "..."], '
    '"reflection": "2-4 sentence thoughtful reflection", '
    '"observations": "1-2 sentence note on patterns, or an empty string if '
    'there is not enough information", '
    '"next_step": "one practical, non-prescriptive suggestion"}\n'
    "Use at most 5 themes."
)


class ReflectAnalysisError(RuntimeError):
    """Raised when the AI reflection could not be generated or parsed."""


class ReflectService:
    def __init__(self):
        self.client = OllamaClient()

    def analyze(self, content: str) -> dict:
        """
        Returns a dict with mood/themes/reflection/observations/next_step.
        Raises ReflectAnalysisError on any failure (Ollama unreachable,
        timed out, or a reply that never resolves to valid JSON) — callers
        are expected to catch this and keep the already-saved journal
        entry intact rather than losing it.
        """
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Journal entry:\n{content.strip()}"},
        ]

        try:
            raw = self.client.chat(
                messages, temperature=0.4, max_tokens=400, timeout=ANALYSIS_TIMEOUT_SECONDS
            )
        except RuntimeError as e:
            raise ReflectAnalysisError(str(e)) from e

        parsed = self._extract_json(raw)
        if parsed is None:
            raise ReflectAnalysisError("AI reflection did not return valid JSON.")

        return self._normalize(parsed)

    @staticmethod
    def _extract_json(raw: str) -> Optional[dict]:
        text = raw.strip()
        # Strip a ```json ... ``` / ``` ... ``` fence some models wrap output in.
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()

        candidates = [text]
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    @staticmethod
    def _normalize(parsed: dict) -> dict:
        mood = parsed.get("mood")
        if not isinstance(mood, str) or mood not in _ALLOWED_MOODS:
            mood = "Mixed"

        themes = parsed.get("themes")
        if not isinstance(themes, list):
            themes = []
        themes = [str(t).strip() for t in themes if str(t).strip()][:_MAX_THEMES]

        def _text(key: str) -> str:
            value = parsed.get(key)
            return value.strip() if isinstance(value, str) else ""

        return {
            "mood": mood,
            "themes": themes,
            "reflection": _text("reflection"),
            "observations": _text("observations"),
            "next_step": _text("next_step"),
        }
