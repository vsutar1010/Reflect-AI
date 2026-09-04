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


class OllamaClient:

    def __init__(self, model: str = OPENROUTER_MODEL):
        self.model = model

    def set_model(self, model: str):
        """Change model during runtime."""
        self.model = model

    def _build_request(
        self,
        messages: List[Dict[str, str]],
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
    ) -> urllib.request.Request:
        payload = {
            "model": self.model,
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
        request = self._build_request(messages, stream=False, temperature=temperature, max_tokens=max_tokens)

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter HTTP Error ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Unable to reach OpenRouter.\n"
                f"Model: {self.model}\n\n"
                f"Check OPENROUTER_API_KEY and network access."
            ) from exc

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
        """
        request = self._build_request(messages, stream=True, temperature=temperature, max_tokens=max_tokens)

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
                        yield token

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter HTTP Error ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Unable to reach OpenRouter.\n"
                f"Model: {self.model}\n\n"
                f"Check OPENROUTER_API_KEY and network access."
            ) from exc

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
