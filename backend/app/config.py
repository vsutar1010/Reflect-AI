"""
Centralized configuration for ReflectAI.

Everything that differs between environments (local dev, a teammate's
machine, production) lives here as an environment variable with a sane
default. Nothing in this file should be secret by itself — real secrets
come from a local .env file (see .env.example) that is never committed.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _positive_int(value: str | None, default: int) -> int:
    """Parses a positive integer from an env var, falling back to
    `default` for anything missing, non-numeric, zero, or negative —
    used for limits where 0/negative would otherwise silently disable
    the protection they're meant to provide."""
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    return parsed if parsed > 0 else default


# ==========================================================
# Ollama (Text Chat + Analysis LLM)
# ==========================================================

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral:7b-instruct-v0.3-q3_K_S")

# ==========================================================
# WhatsApp Chat Import
# ==========================================================
# Plain-text WhatsApp exports ("Export chat -> Without Media") are
# compact — even a multi-year, tens-of-thousands-of-messages 1:1
# history rarely reaches double-digit megabytes. 15MB gives a generous
# margin over any realistic real chat while still bounding worst-case
# memory/CPU usage in app/routers/analyze.py's upload handler and the
# WhatsApp parser it feeds. Invalid/zero/negative values fall back to
# this default rather than silently disabling the limit.
MAX_WHATSAPP_UPLOAD_SIZE_MB = _positive_int(os.environ.get("MAX_WHATSAPP_UPLOAD_SIZE_MB"), 15)
MAX_WHATSAPP_UPLOAD_SIZE_BYTES = MAX_WHATSAPP_UPLOAD_SIZE_MB * 1024 * 1024

# ==========================================================
# MongoDB (profiles + conversation history)
# ==========================================================
# Replaces the old backend/profiles/{uuid}/*.json flat-file storage.
# MONGODB_URI is a full connection string (e.g. from MongoDB Atlas:
# "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority").
MONGODB_URI = os.environ.get("MONGODB_URI", "")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "reflectai")

# ==========================================================
# Authentication
# ==========================================================
# Signs/verifies the session JWT stored in an httpOnly cookie. Required —
# unlike the other config below, there is no safe default for a secret.
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Add it to backend/.env — any long random "
        "string works (e.g. `python -c \"import secrets; print(secrets.token_hex(32))\"`)."
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = int(os.environ.get("JWT_EXPIRE_DAYS", "14"))

SESSION_COOKIE_NAME = "reflectai_session"

# Verifies "Sign in with Google" ID tokens (see app/services/auth_service.py).
# Create a Google Cloud OAuth "Web application" Client ID and set the same
# value here and as VITE_GOOGLE_CLIENT_ID in frontend/.env. Leave blank to
# disable Google Sign-In — email/password auth works without it.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

# The frontend origin allowed to make credentialed (cookie-carrying) requests
# to this API. Browsers reject a wildcard ("*") combined with credentials, so
# this must be an explicit origin — the Vite dev server's by default.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

# Whether the session cookie requires HTTPS. Keep False for local http
# development; set True once the app is served over https in production.
COOKIE_SECURE = _bool(os.environ.get("COOKIE_SECURE"), default=False)

# ==========================================================
# Email (signup OTP verification)
# ==========================================================
# Proves the signup email address is actually reachable by whoever is
# signing up. Not required at import time like JWT_SECRET — the app still
# boots and existing users can still log in without this configured, only
# new signups need it (see app/services/email_service.py).
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "ReflectAI")

OTP_EXPIRE_MINUTES = int(os.environ.get("OTP_EXPIRE_MINUTES", "10"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get("OTP_RESEND_COOLDOWN_SECONDS", "60"))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))


def smtp_configured() -> bool:
    return bool(SMTP_USERNAME and SMTP_PASSWORD)

# ==========================================================
# Public backend URL
# ==========================================================
# Vapi is a cloud service — it cannot reach "localhost". To let Vapi call
# our custom-llm endpoint for every voice turn, this server must be
# reachable from the public internet. In local dev that means a tunnel
# (e.g. `ngrok http 8000`, or `cloudflared tunnel --url http://localhost:8000`).
# Set this to whatever URL that tunnel gives you, e.g.
# "https://abcd1234.ngrok-free.app". In production, set it to your real
# deployed backend URL.
PUBLIC_BACKEND_URL = os.environ.get("PUBLIC_BACKEND_URL", "").rstrip("/")

# ==========================================================
# Vapi
# ==========================================================

# Server-side secret key, used for REST calls to api.vapi.ai (optional —
# only needed if you pre-register assistants or fetch call data via the
# server API instead of the fully-dynamic inline config this project
# uses by default).
VAPI_PRIVATE_KEY = os.environ.get("VAPI_PRIVATE_KEY", "")

# Public key exposed to the browser so the Vapi Web SDK can open a call.
# Also read directly by the frontend via VITE_VAPI_PUBLIC_KEY — kept here
# too so the backend can tell the frontend whether voice is configured.
VAPI_PUBLIC_KEY = os.environ.get("VAPI_PUBLIC_KEY", "")

# Shared secret Vapi sends back on webhook + custom-llm requests so we
# can verify the caller is actually Vapi and not a random request hitting
# our public tunnel URL. Configure the same value in the Vapi dashboard
# under the assistant's server URL secret / custom LLM headers.
VAPI_SERVER_SECRET = os.environ.get("VAPI_SERVER_SECRET", "")

# Vapi's assistant schema has no dedicated "secret" field — just generic
# `headers` maps on `server` (webhooks) and `model` (custom-llm). This is
# the header name we choose to carry VAPI_SERVER_SECRET in both places.
VAPI_SECRET_HEADER = "x-reflectai-secret"

# Optional: a pre-created Vapi Assistant ID to use as a base template
# (transcriber/voice provider settings configured once in the Vapi
# dashboard). When unset, the backend builds a fully inline assistant
# config per call instead — no dashboard setup required.
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID", "")

# Voice (text-to-speech) provider + voice used as the fallback when a
# profile hasn't picked its own voice yet (see VAPI_VOICE_PRESETS below
# for the per-profile male/female options — set via PUT
# /api/profiles/{id}/voice, stored on the profile document).
VAPI_VOICE_PROVIDER = os.environ.get("VAPI_VOICE_PROVIDER", "vapi")
VAPI_VOICE_ID = os.environ.get("VAPI_VOICE_ID", "Elliot")

# Curated presets a profile can pick between. Both are Vapi's own
# built-in "vapi" provider voices (no extra account/credential needed) —
# see docs.vapi.ai/providers/voice/vapi-voices for the full catalog.
# Deliberately keyed by "provider"/"voice_id" (not just a raw voice
# name) so a future per-profile ElevenLabs clone can slot into this same
# shape without a schema change — just a different provider/voice_id.
VAPI_VOICE_PRESETS = {
    "male": {"provider": "vapi", "voice_id": "Elliot"},
    "female": {"provider": "vapi", "voice_id": "Savannah"},
}

# Transcriber (speech-to-text) provider/model/language.
VAPI_TRANSCRIBER_PROVIDER = os.environ.get("VAPI_TRANSCRIBER_PROVIDER", "deepgram")
VAPI_TRANSCRIBER_MODEL = os.environ.get("VAPI_TRANSCRIBER_MODEL", "nova-2")
VAPI_TRANSCRIBER_LANGUAGE = os.environ.get("VAPI_TRANSCRIBER_LANGUAGE", "en")

# Which LLM actually generates voice replies. Both modes build their
# prompt from the exact same TwinContext (see twin_context.py) — what
# differs is which adapter formats it and which model executes it.
#   "vapi-native" (default) -> Vapi's own hosted model (a free
#       OpenRouter model by default) generates replies, using
#       VapiPromptAdapter. A CPU-only
#       local model's time-to-first-token (10-100+ seconds observed on
#       this project) makes it unusable for a live conversation — voice
#       needs a fast model, full stop. Personality still comes from the
#       one analyzed profile; only the execution engine differs from
#       Text Chat.
#   "custom-llm" -> Vapi calls back into THIS backend, which runs the
#       exact same Ollama call as Text Chat (via OllamaPromptAdapter).
#       Kept as a fully-working, configurable option for local-only
#       inference — just expect multi-second-to-multi-minute reply
#       latency on typical local hardware.
VAPI_LLM_PROVIDER = os.environ.get("VAPI_LLM_PROVIDER", "vapi-native")

# Only used when VAPI_LLM_PROVIDER == "vapi-native". provider="openrouter"
# with a free model (model IDs ending in ":free") — no cost, but
# OpenRouter's free catalog rotates (a previous default here 404'd mid-
# project when OpenRouter retired it). If VAPI_NATIVE_MODEL ever starts
# failing with "unavailable for free", check
# https://openrouter.ai/models?max_price=0 for a current one and swap it
# here — no code changes needed, it's just this string.
VAPI_NATIVE_MODEL_PROVIDER = os.environ.get("VAPI_NATIVE_MODEL_PROVIDER", "openrouter")
VAPI_NATIVE_MODEL = os.environ.get("VAPI_NATIVE_MODEL", "google/gemma-4-26b-a4b-it:free")

VOICE_MAX_TOKENS = int(os.environ.get("VOICE_MAX_TOKENS", "60"))
VOICE_TEMPERATURE = float(os.environ.get("VOICE_TEMPERATURE", "0.6"))

# How long Vapi will wait for THIS backend to start streaming tokens back
# on a custom-llm turn before giving up on that turn. Vapi's own default
# is 20s, which a CPU-only local Ollama model can easily blow past for a
# single reply — raise this generously so slow-but-working beats a
# silent timeout. Vapi's own hard ceiling is 300s.
VAPI_CUSTOM_LLM_TIMEOUT_SECONDS = int(os.environ.get("VAPI_CUSTOM_LLM_TIMEOUT_SECONDS", "120"))

# Separate from the above: how long Vapi will let the CALL sit with no
# audio activity before hanging up entirely (endedReason
# "silence-timed-out"). Vapi's platform default here is ~30s, which is
# shorter than VAPI_CUSTOM_LLM_TIMEOUT_SECONDS — meaning the whole call
# can get killed while Ollama is still generating, discarding the reply
# before it ever gets spoken. Keep this comfortably above the custom-llm
# timeout so a slow-but-successful turn survives.
VAPI_SILENCE_TIMEOUT_SECONDS = int(os.environ.get("VAPI_SILENCE_TIMEOUT_SECONDS", "180"))


def voice_status() -> tuple[bool, str]:
    """
    Whether enough Vapi config is present to offer Voice Chat, and if not,
    exactly what's missing — this is surfaced directly in the frontend so
    "not configured" never has to mean "figure out which of six env vars
    I forgot."
    """
    if not VAPI_PUBLIC_KEY:
        return False, "VAPI_PUBLIC_KEY is not set in backend/.env."

    if not PUBLIC_BACKEND_URL:
        return False, (
            "PUBLIC_BACKEND_URL is not set. Vapi needs a public URL to send "
            "webhooks back to this backend — that's how a voice call's "
            "transcript gets synced into shared memory with Text Chat, in "
            "both vapi-native and custom-llm mode. Expose this backend with "
            "a tunnel (e.g. `ngrok http 8000`) and set PUBLIC_BACKEND_URL."
        )

    return True, ""


def voice_enabled() -> bool:
    """Whether enough Vapi config is present to offer Voice Chat at all."""
    return voice_status()[0]


def custom_llm_base_url(session_id: str) -> str:
    """
    Vapi's custom-llm provider uses this as an OpenAI client `baseURL` and
    appends `/chat/completions` itself — do NOT include that suffix here.
    """
    base = PUBLIC_BACKEND_URL or "http://localhost:8000"
    return f"{base}/api/voice/llm/{session_id}"
