"""
TwinContext — the provider-agnostic data bundle DigitalTwinEngine hands to
every prompt adapter.

This is deliberately just data: no formatting, no provider-specific
shaping, no knowledge of Ollama or Vapi. Each adapter (see app/adapters/)
takes one of these and decides how to turn it into whatever its target
LLM actually expects — that's the boundary that keeps DigitalTwinEngine
from needing to know anything about the LLMs consuming its output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TwinContext:
    profile_id: str
    name: str

    # The full, verbose identity prompt generated at analysis time —
    # written with a small local model in mind (heavy repetition, an
    # explicit good/bad example table). Adapters targeting a stronger
    # hosted model are expected to distill this, not just truncate it.
    identity_prompt: str

    # Verbatim quotes from the person's real interview answers, most
    # recent first within the character budget applied when extracted.
    voice_grounding_quotes: List[str]

    personality: Dict = field(default_factory=dict)
    thinking_pattern: Dict = field(default_factory=dict)
    emotional_style: Dict = field(default_factory=dict)
    conversation_behaviour: Dict = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)

    # LLM-generated "Friend: ... / Twin: ..." example exchanges from the
    # analysis phase, if any were produced.
    example_replies: List[Dict] = field(default_factory=list)

    summary: str = ""
    favorite_words: List[str] = field(default_factory=list)
    emojis: List[str] = field(default_factory=list)
    response_length: Dict = field(default_factory=dict)
    greetings: Dict = field(default_factory=dict)
