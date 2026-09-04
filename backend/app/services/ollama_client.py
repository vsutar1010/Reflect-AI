"""
ReflectAI LLM Client

This module is responsible for communicating with OpenRouter's free-tier
hosted models over its OpenAI-compatible chat completions API.

Kept the name `OllamaClient`/`ollama_client.py` (originally a local
Ollama server) to avoid touching every call site — the class still
exposes the same chat/stream_chat/health_check interface, only the
backend behind it changed, so Analysis, Text Chat, and Voice Chat's
custom-llm proxy can run without any local LLM hardware.

All AI interactions (Analysis, Text Chat, and Voice Chat's custom-llm
proxy) go through this client.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, Iterator, List, Optional

from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"

# OpenRouter's free catalog rotates and any given model can be
# temporarily rate-limited on its shared free pool (HTTP 429) or, for
# "thinking"/reasoning models, can spend its whole max_tokens budget on
# hidden reasoning and return no actual content. Rather than surfacing
# that as a failed reply, chat()/stream_chat() fall through this list
# after the configured OPENROUTER_MODEL. Update if these start failing
# too — check https://openrouter.ai/models?max_price=0.
FALLBACK_MODELS = (
    "inclusionai/ling-3.0-flash-fin:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
)


class OllamaClient:

    def __init__(self, model: str = OPENROUTER_MODEL):
        self.model = model

    def set_model(self, model: str):
        """Change model during runtime."""
        self.model = model

    def _model_candidates(self) -> Iterator[str]:
        seen = {self.model}
        yield self.model
        for m in FALLBACK_MODELS:
            if m not in seen:
                seen.add(m)
                yield m

    def _build_request(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
    ) -> urllib.request.Request:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        return urllib.request.Request(
            CHAT_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
            method="POST",
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> str:
        last_error: Optional[Exception] = None

        for model in self._model_candidates():
            request = self._build_request(model, messages, stream=False, temperature=temperature, max_tokens=max_tokens)
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    content = result["choices"][0]["message"].get("content")
                    if content and content.strip():
                        return content
                    last_error = RuntimeError(f"{model} returned no content (likely exhausted max_tokens on reasoning)")
                    continue

            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"OpenRouter HTTP Error ({exc.code}) for {model}: {body}")
                continue
            except urllib.error.URLError as exc:
                last_error = RuntimeError(
                    f"Unable to reach OpenRouter for {model}.\n"
                    f"Check OPENROUTER_API_KEY and network access."
                )
                continue

        raise last_error or RuntimeError("No model candidates configured")

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Yields the reply token-by-token as it's generated, instead of
        waiting for the full reply. Used by the Voice Chat custom-llm
        proxy: streaming the first token to Vapi as soon as it exists is
        the difference between the twin feeling responsive and feeling
        like dead air on a phone call.

        Falls through FALLBACK_MODELS the same way chat() does, but only
        before any token has been yielded for the current turn — once
        output has started reaching the caller, a failure is raised
        directly instead of restarting the reply with a different model
        mid-stream.
        """
        last_error: Optional[Exception] = None

        for model in self._model_candidates():
            request = self._build_request(model, messages, stream=True, temperature=temperature, max_tokens=max_tokens)
            produced_any = False
            try:
                with urllib.request.urlopen(request) as response:
                    while True:
                        line = response.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8").strip()
                        if not decoded or not decoded.startswith("data:"):
                            continue
                        data = decoded[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        token = chunk["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            produced_any = True
                            yield token

                if produced_any:
                    return
                last_error = RuntimeError(f"{model} returned no content (likely exhausted max_tokens on reasoning)")
                continue

            except urllib.error.HTTPError as exc:
                if produced_any:
                    body = exc.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"OpenRouter HTTP Error ({exc.code}) for {model}: {body}") from exc
                body = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"OpenRouter HTTP Error ({exc.code}) for {model}: {body}")
                continue
            except urllib.error.URLError as exc:
                if produced_any:
                    raise RuntimeError(f"Unable to reach OpenRouter for {model} mid-stream.") from exc
                last_error = RuntimeError(f"Unable to reach OpenRouter for {model}.")
                continue

        raise last_error or RuntimeError("No model candidates configured")

    def health_check(self) -> bool:
        """Returns True if OpenRouter is reachable with the configured key."""
        try:
            request = urllib.request.Request(
                MODELS_ENDPOINT,
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            )
            urllib.request.urlopen(request, timeout=5)
            return True
        except Exception:
            return False
