"""
Shared Ollama Client for ReflectAI

Used by:
- analyzer.py
- chat.py
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

OLLAMA_HOST = os.environ.get(
    "OLLAMA_HOST",
    "http://localhost:11434"
).rstrip("/")

MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "mistral:7b-instruct-v0.3-q3_K_S"
)

CHAT_URL = f"{OLLAMA_HOST}/api/chat"


class OllamaClient:

    def __init__(self, model: str = MODEL):
        self.model = model

    def chat(self, messages, stream=True):

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }

        request = urllib.request.Request(
            CHAT_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(request) as response:

                if not stream:
                    data = json.loads(response.read().decode())
                    return data["message"]["content"]

                full_response = ""

                while True:

                    line = response.readline()

                    if not line:
                        break

                    decoded = line.decode().strip()

                    if not decoded:
                        continue

                    chunk = json.loads(decoded)

                    token = chunk.get(
                        "message",
                        {}
                    ).get(
                        "content",
                        ""
                    )

                    if token:
                        print(token, end="", flush=True)
                        full_response += token

                    if chunk.get("done"):
                        break

                print()

                return full_response

        except urllib.error.URLError:

            print("\nCould not connect to Ollama.")
            print("Start Ollama first.")
            raise

        except urllib.error.HTTPError as exc:

            print(f"\nHTTP Error : {exc.code}")

            raise