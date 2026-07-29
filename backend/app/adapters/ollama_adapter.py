"""
OllamaPromptAdapter — turns a TwinContext into the message list Ollama
expects.

This is deliberately verbose and repetitive: a small quantized local
model needs heavy repetition and explicit good/bad examples to reliably
follow instructions. Contrast with VapiPromptAdapter, which targets a
much stronger hosted model and is written completely differently as a
result — that's the point of splitting these into separate adapters
instead of one prompt with a "shorter for Vapi" branch.

Used by TextChatService always, and by VoiceChatService when
VAPI_LLM_PROVIDER=custom-llm (that mode routes voice replies through
Ollama too, so it should sound exactly like Text Chat).
"""

from __future__ import annotations

from typing import Dict, List

from app.services.twin_context import TwinContext


def _build_voice_grounding_block(quotes: List[str]) -> str:
    formatted = "\n".join(f"- {line}" for line in quotes)

    return f"""
REAL MESSAGES FROM THIS PERSON — verbatim quotes from an earlier
conversation with them. These are not something you wrote. Study them
silently to absorb their exact vocabulary, spelling habits, punctuation,
sentence length, slang, and tone. Treat this as the strongest signal for
how they actually write — stronger than any description below.

--------------------------------------------------

{formatted}

--------------------------------------------------

Never quote these lines back verbatim unless it naturally fits the
conversation. Never mention that you were shown these messages. Just let
them quietly shape how you naturally write.
"""


def build_messages(context: TwinContext) -> List[Dict[str, str]]:
    messages = [{"role": "system", "content": context.identity_prompt}]

    if context.voice_grounding_quotes:
        messages.append({"role": "system", "content": _build_voice_grounding_block(context.voice_grounding_quotes)})

    return messages
