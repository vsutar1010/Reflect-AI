"""
VapiPromptAdapter — turns a TwinContext into a single system prompt for
Vapi's hosted model (default: GPT-4o-mini via VAPI_LLM_PROVIDER=vapi-native).

This is NOT a shortened version of OllamaPromptAdapter's output. A small
quantized local model needs heavy repetition and an explicit good/bad
example table to reliably follow instructions; a hosted frontier model
doesn't — spending tokens on that repetition here would only add cost
and latency without improving compliance. This adapter is written from
scratch for what a strong model actually needs: a concise persona, a
curated sample of real quotes, and a short list of hard rules.

It also frames identity differently on purpose: Ollama's prompt is
written for texting (WhatsApp-style). This one is written for a live
spoken phone call — no emojis, shorter replies, natural spoken cadence
instead of written cadence. Voice and text are the same person, but they
don't sound identical in the two mediums, and pretending otherwise would
make voice replies read like text messages read aloud.
"""

from __future__ import annotations

from app.services.twin_context import TwinContext

MAX_QUOTES = 15
MAX_EXAMPLE_REPLIES = 4


def _render_traits(traits: dict) -> str:
    parts = []
    for key, value in traits.items():
        if value is True:
            parts.append(key.replace("_", " "))
        elif value is False:
            continue
        elif isinstance(value, dict):
            nested = _render_traits(value)
            if nested:
                parts.append(nested)
        elif isinstance(value, (list, tuple)):
            if value:
                parts.append(", ".join(str(v) for v in value))
        elif value:
            parts.append(f"{key.replace('_', ' ')}: {value}")
    return ", ".join(parts)


def build_prompt(context: TwinContext) -> str:
    quotes = context.voice_grounding_quotes[-MAX_QUOTES:]
    quotes_block = "\n".join(f'- "{q}"' for q in quotes) if quotes else "(none captured yet)"

    traits = _render_traits(context.personality)
    emotional = _render_traits(context.emotional_style)
    behaviour = _render_traits(context.conversation_behaviour)

    examples = context.example_replies[:MAX_EXAMPLE_REPLIES]
    examples_block = ""
    if examples:
        lines = "\n".join(
            f'- Friend: "{ex.get("friend", "")}" -> You: "{ex.get("twin", "")}"'
            for ex in examples
            if ex.get("friend") and ex.get("twin")
        )
        if lines:
            examples_block = f"\n\nHow you actually reply in conversation:\n{lines}"

    who = context.name or "this person"

    return f"""You are {who}, talking on a live voice call with someone you know. You are NOT an AI assistant, NOT a character, NOT ChatGPT. You ARE this person. Never reveal you're an AI, and never mention a personality analysis or profile.

REAL THINGS THEY'VE SAID — study these for their exact vocabulary, tone, and phrasing:
{quotes_block}{examples_block}

VOICE RULES — this is spoken, not texted:
- Keep replies short: almost always one sentence, rarely two. This is a real-time back-and-forth, not a monologue.
- Speak the way people actually talk out loud — contractions, casual grammar, natural pauses. Not written-language phrasing.
- Never use emojis or emoticons; this is spoken aloud, not read.
- Never sound like customer support. Never say "How can I help you" or "What can I do for you."
- Don't end every reply with a question. Plenty of real replies are just statements.
- Don't repeat greetings once the conversation is already going.
- React the way they actually would, not with a scripted acknowledgement like "I'm glad to hear that."

WHO THEY ARE:
{context.summary or "No summary available."}
Interests: {", ".join(context.interests) if context.interests else "unknown"}
Personality: {traits or "unknown"}
Emotional style: {emotional or "unknown"}
Conversation style: {behaviour or "unknown"}

Always sound like the real person talking. The goal is realism, not correctness."""
