"""
ReflectAI Ollama Client

This module is responsible for communicating with the local
Ollama server.

All AI interactions (Analysis, Text Chat, and Voice Chat's custom-llm
proxy) go through this client.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, Iterator, List, Optional

from app.config import OLLAMA_HOST, OLLAMA_MODEL

CHAT_ENDPOINT = f"{OLLAMA_HOST}/api/chat"


class OllamaClient:

    def __init__(self, model: str = OLLAMA_MODEL):
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
        options = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": options,
        }

        return urllib.request.Request(
            CHAT_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
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
        request = self._build_request(messages, stream, temperature, max_tokens)

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if not stream:
                    result = json.loads(response.read().decode("utf-8"))
                    return result["message"]["content"]

                complete_response = ""
                while True:
                    line = response.readline()
                    if not line:
                        break
                    decoded = line.decode().strip()
                    if not decoded:
                        continue
                    chunk = json.loads(decoded)
                    complete_response += chunk.get("message", {}).get("content", "")
                    if chunk.get("done"):
                        break

                return complete_response

        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Ollama HTTP Error ({exc.code})") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Unable to connect to Ollama.\n"
                f"Host : {OLLAMA_HOST}\n"
                f"Model: {self.model}\n\n"
                f"Make sure Ollama is running."
            ) from exc

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Yields the reply token-by-token as Ollama generates it, instead of
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
                    decoded = line.decode().strip()
                    if not decoded:
                        continue
                    chunk = json.loads(decoded)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break

        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Ollama HTTP Error ({exc.code})") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Unable to connect to Ollama.\n"
                f"Host : {OLLAMA_HOST}\n"
                f"Model: {self.model}\n\n"
                f"Make sure Ollama is running."
            ) from exc

    def health_check(self) -> bool:
        """Returns True if Ollama server is reachable."""
        try:
            request = urllib.request.Request(OLLAMA_HOST, method="GET")
            urllib.request.urlopen(request)
            return True
        except Exception:
            return False
