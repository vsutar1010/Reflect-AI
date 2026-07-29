"""
Thin wrapper around Vapi's server-side concerns:
  - verifying that a webhook/custom-llm request actually came from Vapi
  - optional REST calls to api.vapi.ai (fetching a call's official record)

This project does NOT pre-register a Vapi Assistant via the REST API by
default — VoiceChatService builds a fully inline assistant config per
call instead, so no dashboard setup is required to get started. This
client exists for the pieces that genuinely need server-to-server calls:
webhook verification, and optionally reconciling a call's transcript
after the fact.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from app.config import VAPI_PRIVATE_KEY, VAPI_SERVER_SECRET

VAPI_API_BASE = "https://api.vapi.ai"


def verify_server_secret(header_value: Optional[str]) -> bool:
    """
    Checks the shared-secret header (see app.config.VAPI_SECRET_HEADER)
    we configure on the assistant's `server.headers` (webhooks) and
    `model.headers` (custom-llm) — Vapi's assistant schema has no
    dedicated secret field, so this is a custom header we set and verify
    ourselves. If we haven't configured a secret (VAPI_SERVER_SECRET is
    empty), requests are allowed through — useful for local development
    before secrets are set up, but you should set one before exposing
    this publicly.
    """
    if not VAPI_SERVER_SECRET:
        return True
    return header_value == VAPI_SERVER_SECRET


class VapiClient:
    def __init__(self, private_key: str = VAPI_PRIVATE_KEY):
        self.private_key = private_key

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        if not self.private_key:
            raise RuntimeError("VAPI_PRIVATE_KEY is not configured.")

        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{VAPI_API_BASE}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {self.private_key}",
                "Content-Type": "application/json",
            },
            method=method,
        )

        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Vapi API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Unable to reach Vapi API: {exc}") from exc

    def fetch_call(self, call_id: str) -> dict:
        """Fetches a call's official record (status, transcript, cost, etc)."""
        return self._request("GET", f"/call/{call_id}")
