"""
ReflectAI Ollama Client

This module is responsible for communicating with the local
Ollama server.

All AI interactions (Analysis & Chat) go through this client.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, List


OLLAMA_HOST = os.environ.get(
    "OLLAMA_HOST",
    "http://localhost:11434"
).rstrip("/")


OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL",
"llama3:latest"
)


CHAT_ENDPOINT = f"{OLLAMA_HOST}/api/chat"


class OllamaClient:

    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model

    def set_model(self, model: str):
        """
        Change model during runtime.
        """

        self.model = model

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
    ) -> str:

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }

        request = urllib.request.Request(
            CHAT_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(request) as response:

                # Non Streaming
                if not stream:

                    result = json.loads(
                        response.read().decode("utf-8")
                    )

                    return result["message"]["content"]

                # Streaming

                complete_response = ""

                while True:

                    line = response.readline()

                    if not line:
                        break

                    decoded = line.decode().strip()

                    if not decoded:
                        continue

                    chunk = json.loads(decoded)

                    token = (
                        chunk
                        .get("message", {})
                        .get("content", "")
                    )

                    complete_response += token

                    if chunk.get("done"):
                        break

                return complete_response

        except urllib.error.HTTPError as exc:

            raise RuntimeError(
                f"Ollama HTTP Error ({exc.code})"
            ) from exc

        except urllib.error.URLError as exc:

            raise RuntimeError(
                f"Unable to connect to Ollama.\n"
                f"Host : {OLLAMA_HOST}\n"
                f"Model: {self.model}\n\n"
                f"Make sure Ollama is running."
            ) from exc

    def health_check(self) -> bool:
        """
        Returns True if Ollama server is reachable.
        """

        try:

            request = urllib.request.Request(
                OLLAMA_HOST,
                method="GET"
            )

            urllib.request.urlopen(request)

            return True

        except Exception:

            return False