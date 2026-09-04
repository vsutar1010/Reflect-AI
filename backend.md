# ReflectAI — Backend Documentation

> **Purpose:** Complete reference for the FastAPI Python backend. Feed this file to any AI to get full context — every router, service, endpoint, and storage schema is documented here.
> **Last Updated:** 2026-09-04 | **API Version:** 2.0.0

---

## Tech Stack

| Tool | Purpose |
|------|------|
| Python 3.10+ | Language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server (`--reload` enabled via `run.py`) |
| Pydantic v2 | Request/response schema validation (`app/schemas.py`) |
| Ollama | Local LLM inference (analysis, text chat, Reflect, custom-llm voice) |
| pymongo + dnspython + certifi | MongoDB driver (Atlas `mongodb+srv://` support + TLS) |
| PyJWT | Session cookie signing/verification |
| bcrypt | Password hashing |
| google-auth | Google ID token verification (Sign-In with Google) |
| smtplib (stdlib) | Sends the signup OTP email |
| emoji | Emoji detection in communication analysis |
| python-dotenv | `.env` loading |
| @vapi-ai/web | Vapi Web SDK (frontend, not backend) |

**Default LLM model:** `mistral:7b-instruct-v0.3-q3_K_S` (configurable via `OLLAMA_MODEL`).
**Database:** MongoDB (Atlas or self-hosted, via `MONGODB_URI`) — the only storage; there is no file-based fallback. In-progress analysis/chat/voice *sessions* and the auth rate limiters remain in-memory dicts, not persisted.

---

## Full Folder Structure

```
backend/
├── run.py                                  # Entry point — starts uvicorn server
├── .env                                    # Environment secrets (never committed)
├── .env.example                            # Template for all env vars
├── requirements.txt                        # Python dependencies
└── app/
    ├── __init__.py
    ├── main.py                             # FastAPI app, router registration, middleware
    ├── schemas.py                          # Pydantic request/response models
    ├── config.py                           # Centralized env var config
    ├── database.py                         # MongoDB client + collections
    ├── dependencies.py                     # Shared service singletons + get_current_user
    ├── middleware.py                       # MaxUploadSizeMiddleware (WhatsApp import)
    ├── adapters/
    │   ├── ollama_adapter.py               # TwinContext → Ollama message list
    │   └── vapi_adapter.py                 # TwinContext → Vapi system prompt string
    ├── routers/
    │   ├── auth.py                         # POST /api/auth/*
    │   ├── analyze.py                      # POST /api/analyze/* + WhatsApp import
    │   ├── chat.py                         # POST /api/chat/* (JSON + SSE)
    │   ├── profiles.py                     # GET/PUT/DELETE /api/profiles/*
    │   ├── reflect.py                      # CRUD /api/reflect/*
    │   └── voice.py                        # GET/POST /api/voice/* + SSE + webhook
    └── services/
        ├── auth_service.py                 # Password hashing, JWTs, Google verification
        ├── email_service.py                # SMTP OTP delivery
        ├── rate_limiter.py                 # In-memory fixed-window rate limiter
        ├── analyzer.py                     # PersonalityAnalyzer — interview orchestration
        ├── communication_analyzer.py       # CommunicationAnalyzer — pure Python NLP + LLM prompt
        ├── whatsapp_parser.py              # WhatsApp .txt export → messages
        ├── whatsapp_import_service.py      # Upload/finalize orchestration
        ├── twin_engine.py                  # DigitalTwinEngine — shared brain (text + voice)
        ├── twin_context.py                 # TwinContext dataclass
        ├── chat.py                         # TextChatService — text chat + summarization
        ├── voice_chat_service.py           # VoiceChatService — Vapi voice integration
        ├── vapi_client.py                  # Webhook secret verification + REST
        ├── reflect_service.py              # ReflectService — AI journaling analysis
        └── ollama_client.py                # OllamaClient — HTTP wrapper for Ollama REST API
```

---

## How to Run Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
# Server starts at http://0.0.0.0:8000, reload enabled
```

**Requires, always:**
- Ollama running locally with a model pulled (`ollama pull mistral:7b-instruct-v0.3-q3_K_S`, `ollama serve`)
- `MONGODB_URI` set in `.env` — the backend pings MongoDB on startup and fails fast if it can't connect
- `JWT_SECRET` set in `.env` — the backend refuses to start without it (signs the session cookie)

**For signup to work:** `SMTP_USERNAME`/`SMTP_PASSWORD` set (existing users can still log in without this).

**For Voice Chat:** `VAPI_PUBLIC_KEY` + `PUBLIC_BACKEND_URL` (a public tunnel, e.g. ngrok) set — see `README.md` step 7.

---

## backend/app/config.py — Centralized Configuration

All environment variables with defaults, loaded from `.env`. See `backend/.env.example` for the fully commented template.

### Ollama
| Var | Default |
|-----|---------|
| `OLLAMA_HOST` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `mistral:7b-instruct-v0.3-q3_K_S` |

### WhatsApp Import
| Var | Default | Notes |
|-----|---------|-------|
| `MAX_WHATSAPP_UPLOAD_SIZE_MB` | `15` | Invalid/zero/negative values fall back to the default rather than disabling the limit (`_positive_int` helper) |

### MongoDB
| Var | Default |
|-----|---------|
| `MONGODB_URI` | `""` (required — raises `RuntimeError` at import time if unset) |
| `MONGODB_DB_NAME` | `reflectai` |

### Authentication
| Var | Default | Notes |
|-----|---------|-------|
| `JWT_SECRET` | *(required, no default)* | Raises `RuntimeError` at import time if unset |
| `JWT_ALGORITHM` | `HS256` | Not env-configurable |
| `JWT_EXPIRE_DAYS` | `14` | |
| `SESSION_COOKIE_NAME` | `reflectai_session` | Not env-configurable |
| `GOOGLE_CLIENT_ID` | `""` | Blank disables Google Sign-In |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS `allow_origins`, must be exact (credentialed requests can't use `*`) |
| `COOKIE_SECURE` | `False` | Set `true` once served over HTTPS |
| `AUTH_LOGIN_MAX_ATTEMPTS` / `AUTH_LOGIN_WINDOW_SECONDS` | `5` / `900` | Failed login attempts per client IP |
| `AUTH_OTP_REQUEST_MAX_ATTEMPTS` / `AUTH_OTP_REQUEST_WINDOW_SECONDS` | `5` / `900` | Signup OTP requests per client IP |

### Email (signup OTP)
| Var | Default |
|-----|---------|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | `""` |
| `SMTP_FROM_NAME` | `ReflectAI` |
| `OTP_EXPIRE_MINUTES` | `10` |
| `OTP_RESEND_COOLDOWN_SECONDS` | `60` |
| `OTP_MAX_ATTEMPTS` | `5` |

`smtp_configured() -> bool` — whether `SMTP_USERNAME`/`SMTP_PASSWORD` are both set.

### Vapi (Voice Chat)
| Var | Default | Description |
|-----|---------|-------------|
| `PUBLIC_BACKEND_URL` | `""` | Public tunnel URL, required for Voice Chat |
| `VAPI_PUBLIC_KEY` / `VAPI_PRIVATE_KEY` | `""` | Browser SDK key / server REST key (optional) |
| `VAPI_SERVER_SECRET` | `""` | Verifies webhook/custom-llm requests actually came from Vapi |
| `VAPI_ASSISTANT_ID` | `""` | Optional pre-created assistant template |
| `VAPI_VOICE_PROVIDER` / `VAPI_VOICE_ID` | `vapi` / `Elliot` | TTS fallback when a profile hasn't picked one — see `VAPI_VOICE_PRESETS` (male→Elliot, female→Savannah, set via `PUT /api/profiles/{id}/voice`) |
| `VAPI_TRANSCRIBER_PROVIDER/MODEL/LANGUAGE` | `deepgram` / `nova-2` / `en` | STT |
| `VAPI_LLM_PROVIDER` | `vapi-native` | `vapi-native` (default, fast, hosted) or `custom-llm` (local Ollama, slow) |
| `VAPI_NATIVE_MODEL_PROVIDER` / `VAPI_NATIVE_MODEL` | `openrouter` / `google/gemma-4-26b-a4b-it:free` | Only used in `vapi-native` mode |
| `VOICE_MAX_TOKENS` / `VOICE_TEMPERATURE` | `60` / `0.6` | |
| `VAPI_CUSTOM_LLM_TIMEOUT_SECONDS` | `120` | `custom-llm` mode only |
| `VAPI_SILENCE_TIMEOUT_SECONDS` | `180` | `custom-llm` mode only |

`voice_status() -> (bool, str)` / `voice_enabled() -> bool` — whether enough config is present, surfaced to the frontend via `GET /api/voice/config`.
`custom_llm_base_url(session_id) -> str` — builds the per-session custom-llm base URL.

---

## backend/app/database.py — MongoDB Connection

One `MongoClient` created at import time (thread-safe, pools connections). Fails fast (`RuntimeError`) if `MONGODB_URI` is unset or unparseable.

```python
profiles_collection      = db["profiles"]
conversations_collection = db["conversations"]
users_collection         = db["users"]
reflections_collection   = db["reflections"]
```

- `ping()` — called on startup; a bad `MONGODB_URI` fails immediately instead of surfacing as a confusing 500 later.
- `init_indexes()` — `conversations.profile_id`, `profiles.owner_id`, `users.email` (unique), `users.google_sub` (unique, sparse), `reflections.(owner_id, created_at)`, `reflections.profile_id`.

---

## backend/app/main.py — FastAPI App

```python
app = FastAPI(title="ReflectAI API", version="2.0.0")

app.add_middleware(MaxUploadSizeMiddleware, path="/api/analyze/whatsapp/upload", ...)
app.add_middleware(CORSMiddleware, allow_origins=[config.FRONTEND_ORIGIN],
                    allow_credentials=True, expose_headers=["Retry-After"])

app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(profiles.router)
app.include_router(reflect.router)

@app.on_event("startup")
def on_startup():
    database.ping()
    database.init_indexes()
```

`MaxUploadSizeMiddleware` (added before `CORSMiddleware`, so it ends up as the *inner* layer and CORS headers still apply to its own `413` response) rejects an oversized WhatsApp upload by `Content-Length` before Starlette parses the multipart body at all. `expose_headers=["Retry-After"]` is required because that header isn't CORS-safelisted by default — without it the frontend's 429 handling couldn't read it cross-origin.

`allow_origins` is a single explicit origin (`FRONTEND_ORIGIN`), not `"*"` — browsers reject a wildcard combined with `allow_credentials=True`, which this app needs for the session cookie.

---

## backend/app/schemas.py — Pydantic Models (by API area)

**Auth:** `SignupRequest` (email, password min 8, name), `VerifyOtpRequest` (email, 6-digit otp), `LoginRequest`, `GoogleAuthRequest` (credential), `UserResponse` (id, email, name)

**Analysis:** `StartAnalysisResponse`, `AnalysisMessageRequest/Response` (progress 0-100), `FinalizeAnalysisRequest` (profile_name optional)

**WhatsApp:** `WhatsAppParticipant`, `WhatsAppUploadResponse` (upload_id, participants, total/system/media/deleted message counts), `WhatsAppFinalizeRequest`

**Chat:** `StartChatRequest/Response` (history: List[`ChatHistoryMessage`]), `ChatMessageRequest/Response`

**Voice:** `VoiceConfigResponse`, `StartVoiceSessionRequest/Response`, `EndVoiceSessionRequest`, `VoiceSessionStatusResponse`, `SetProfileVoiceRequest` (gender: "male"|"female")

**Reflect:** `ReflectAnalysis` (status, mood, themes, reflection, observations, next_step, error), `CreateReflectEntryRequest`/`UpdateReflectEntryRequest` (content, 1-8000 chars), `ReflectEntryResponse`

**Generic:** `SuccessResponse`, `ErrorResponse`

`PersonalityProfile` is defined but not used as a `response_model` anywhere (profiles are returned as raw dicts).

---

## All API Endpoints

### Auth (routers/auth.py)

| Endpoint | Notes |
|---|---|
| `POST /api/auth/signup/request-otp` | Rate-limited per IP. Always returns the same generic `200` regardless of whether the email is new, already registered, or on resend cooldown (enumeration protection). Real path: generates a 6-digit OTP, emails it, stores a pending signup in memory. Fake path: pays an equivalent bcrypt-hash + dummy-SMTP-connect cost so timing doesn't distinguish the cases either. |
| `POST /api/auth/signup/verify-otp` | Matches OTP against the pending signup; on success creates the user and sets the session cookie. `400` on expired/missing/wrong code or too many attempts. |
| `POST /api/auth/login` | Rate-limited per IP (failed attempts only; success resets the counter). `401 "Invalid email or password."` for nonexistent email, wrong password, *and* Google-only accounts alike — same status/body/timing (dummy bcrypt hash used when there's no real password to check). `429` + `Retry-After` once the limit is hit. |
| `POST /api/auth/google` | Verifies the Google ID token server-side; finds-or-creates the user (links by email if a password account with the same email exists), sets the session cookie. |
| `POST /api/auth/logout` | Clears the session cookie. |
| `GET /api/auth/me` | Returns the current user (requires the session cookie). |

### Analysis + WhatsApp Import (routers/analyze.py)

| Endpoint | Notes |
|---|---|
| `POST /api/analyze/start` | Creates an in-memory session owned by `current_user`, returns the first question. |
| `POST /api/analyze/message` | Appends the answer, runs `CommunicationAnalyzer`, generates an AI follow-up (or falls back to the question bank). Returns `{question: "", progress: 100}` when the bank is exhausted. |
| `POST /api/analyze/finalize` | Runs full personality analysis, builds `identity_prompt`, inserts into MongoDB `profiles`, deletes the session. |
| `POST /api/analyze/whatsapp/upload` | `.txt` only. Reads in 1MB chunks, aborts with `413` the instant the running total exceeds `MAX_WHATSAPP_UPLOAD_SIZE_MB` — never materializes an oversized file. Returns participants + message counts. |
| `POST /api/analyze/whatsapp/finalize` | Runs the picked sender's messages through the same analysis pipeline as the interview flow. |

### Chat (routers/chat.py)

| Endpoint | Notes |
|---|---|
| `POST /api/chat/start` | Requires the profile to be owned by `current_user`. Creates a session via `TextChatService`, returns the opening line (no LLM call) + existing history. |
| `POST /api/chat/message` | Session ownership checked (`session.owner_id == current_user.id`). **`Accept: text/event-stream`** → `StreamingResponse` of `data: {"delta": "..."}` frames ending in `data: {"done": true}` (or `data: {"error": "..."}`). Any other `Accept` → plain JSON `{reply}` (kept for non-browser callers). Both paths run the exact same context-build + summarization-catch-up logic; the reply is persisted to MongoDB either way. |

### Profiles (routers/profiles.py)

| Endpoint | Notes |
|---|---|
| `GET /api/profiles` | Lists the current user's profiles, sorted by `last_used` desc, with `conversation_count`. |
| `GET /api/profiles/{id}` | 404 if not owned by `current_user`. Returns `{metadata, profile}`. |
| `PUT /api/profiles/{id}/voice` | Sets `{gender: "male"|"female"}` → resolves to a `VAPI_VOICE_PRESETS` entry, stored on the profile. |
| `DELETE /api/profiles/{id}` | Also deletes all `conversations` documents for that profile. |
| `GET /api/profiles/{id}/conversations` | Lists chat threads (today, only `"default"` is ever created) with message count and `updated_at`. |

### Reflect (routers/reflect.py)

| Endpoint | Notes |
|---|---|
| `POST /api/reflect` | Requires an owned `profile_id`. Saves the entry first, then runs AI analysis; the entry is returned either way, `analysis.status` is `"ready"` or `"failed"`. |
| `GET /api/reflect` | Query params `profile_id` (optional filter), `limit` (default 20, max 50), `skip`. Always scoped to `current_user`. |
| `GET /api/reflect/{id}` | 404 if not owned. |
| `PATCH /api/reflect/{id}` | Updates content, clears the old analysis to `{"status": "pending"}` immediately, re-runs analysis against the new text. |
| `POST /api/reflect/{id}/analyze` | Re-runs analysis on the entry's current text ("try again" after a failure). |
| `DELETE /api/reflect/{id}` | |

### Voice (routers/voice.py)

| Endpoint | Notes |
|---|---|
| `GET /api/voice/config` | `{enabled, public_key, llm_provider, reason}` — tells the frontend whether/why voice isn't configured. |
| `POST /api/voice/start` | Requires an owned profile. `503` if voice isn't configured. Returns the full inline Vapi assistant config. |
| `POST /api/voice/end` | Session ownership checked. |
| `GET /api/voice/session/{id}` | Status + duration. |
| `POST /api/voice/webhook` | Verifies `x-reflectai-secret` header (skipped if `VAPI_SERVER_SECRET` is unset — open for local dev). Handles `status-update` and `end-of-call-report`. |
| `POST /api/voice/llm/{session_id}/chat/completions` | `custom-llm` mode only. OpenAI-compatible SSE (or non-streaming JSON if `stream: false`). Verifies the secret header. |

---

## backend/app/services/twin_engine.py — DigitalTwinEngine

**Purpose:** Shared "brain" behind every digital twin — both `TextChatService` and `VoiceChatService` use it. **Constant:** `MAX_HISTORY = 20`.

| Method | Description |
|--------|-------------|
| `load_profile` / `load_metadata` / `load_source_conversation` | Read fields off the `profiles` document |
| `get_voice_config(profile_id)` | Per-profile chosen Vapi voice, or `None` |
| `touch_last_used(profile_id)` | Updates `last_used` |
| `build_twin_context(profile_id)` | Builds + caches the provider-agnostic `TwinContext` (identity, voice-grounding quotes, personality, interests, etc.) |
| `build_dynamic_context(recent_user_messages)` | Mood-adaptation system-message text |
| `build_opening_line(profile_id)` | Instant greeting from communication stats, no LLM call |
| `load_history` / `save_history` / `append_message` | Read/write the `conversations` document's `messages` array |
| `get_summary_state(profile_id, thread)` | `{summary, summarized_through}` — read failures return the safe empty state, never raise |
| `save_summary_state(profile_id, summary, summarized_through, thread)` | Persists the running summary; never touches `messages` |
| `get_recent_user_messages(history, limit=5)` | Last N user message strings |
| `build_context_window(system_messages, history, dynamic_context=None, summary=None, max_history=20)` | Final message list: system messages, then (if given) the summary as a system message, then (if given) dynamic context, then `history[-max_history:]` |
| `invalidate_cache(profile_id)` | Clears the cached `TwinContext` |

---

## backend/app/services/chat.py — TextChatService

**Constants:** `MAX_HISTORY` (imported from `twin_engine`), `MIN_MESSAGES_TO_SUMMARIZE = 2`.

| Method | Description |
|--------|-------------|
| `create_session(session_id, profile_id, owner_id)` | Builds system messages + loads history via the engine |
| `chat(session_id, message)` | Full-reply turn: append user msg → catch up summary → build context window → `OllamaClient.chat(temperature=0.6, max_tokens=60)` → append reply → `{"reply": ...}` |
| `stream_chat(session_id, message)` | Same turn, but yields tokens as `OllamaClient.stream_chat()` produces them; appends the joined full reply at the end |
| `_catch_up_summary(profile_id, history)` | Computes `upto = max(0, len(history) - MAX_HISTORY)` and folds anything new before that point into the running summary |
| `_fold_into_summary(profile_id, history, upto, thread)` | The one real AI-summarization call site. Skips the AI call if there's nothing new to fold, or (below `MIN_MESSAGES_TO_SUMMARIZE`) if there's no existing summary yet. Never raises — falls back to the last known-good summary on any Ollama/Mongo failure. |
| `summarize_conversation(session_id)` | On-demand "summarize everything so far" — funnels through the same `_fold_into_summary`, so it can never create a second, divergent summary |
| `export_chat` / `conversation_stats` | Session introspection helpers |

---

## backend/app/services/voice_chat_service.py — VoiceChatService

**LLM modes (`VAPI_LLM_PROVIDER`):** `vapi-native` (default) — Vapi's own hosted model generates every reply. `custom-llm` — every reply routes through this backend's own Ollama call.

| Method | Description |
|--------|-------------|
| `is_configured()` | `config.voice_enabled()` |
| `start_session(profile_id, owner_id)` | Loads twin context + history, writes the opening line to shared memory immediately, builds the assistant config |
| `build_assistant_config(session_id, opening_line)` | Full inline Vapi assistant JSON — voice, transcriber, `firstMessage`, `model` (shape depends on `llm_provider`), `server` |
| `stream_turn(session_id, incoming_messages)` | `custom-llm` handler: appends the latest user utterance, builds dynamic context, **reads the persisted conversation summary** (read-only — `TextChatService` is what keeps it caught up), builds the context window, streams Ollama tokens, appends the reply |
| `handle_webhook_event(payload)` | `status-update` → `mark_call_started` / ended; `end-of-call-report` → ended + (vapi-native only) `_sync_transcript_from_report` backfills the whole call transcript into shared memory |
| `mark_call_started` / `end_session` | Session lifecycle |

---

## backend/app/services/reflect_service.py — ReflectService

Stateless — each journal entry is analyzed independently via one Ollama call (temperature 0.4, max_tokens 400, 45s timeout). System prompt explicitly forbids diagnosing mental health conditions or inventing facts not in the entry, and keeps "observations" (patterns) separate from "reflection" (interpretation). Parses the model's JSON response (with a fenced-code-block strip + brace-extraction fallback); normalizes `mood` to one of `Positive|Negative|Neutral|Mixed` (defaults to `Mixed` if invalid), caps `themes` at 5. Raises `ReflectAnalysisError` on any failure — the router catches this and stores `{"status": "failed", "error": ...}` instead of losing the entry.

---

## backend/app/services/auth_service.py, email_service.py, rate_limiter.py

**auth_service.py** (stateless, no DB access):
- `hash_password` / `verify_password` — bcrypt
- `create_access_token(user_id)` / `decode_access_token(token)` — JWT, `JWT_SECRET`/`JWT_ALGORITHM`/`JWT_EXPIRE_DAYS`
- `verify_google_id_token(credential)` — verifies against `GOOGLE_CLIENT_ID`, returns `{sub, email, name}`; raises `ValueError` on anything invalid

**email_service.py:**
- `send_otp_email(to_email, name, otp)` — sends the real code via SMTP
- `touch_smtp_connection()` — opens and immediately closes an authenticated SMTP connection without sending, used by `signup/request-otp`'s "skip the real send" branch so that path pays the same latency as a real send (closes a timing side-channel that would otherwise reveal account existence)

**rate_limiter.py** — `RateLimiter(max_events, window_seconds)`: fixed-window per-key counter, a `threading.RLock` per key (not one global lock, so unrelated clients never contend). `guard(key)` raises `RateLimitExceeded` immediately if already blocked, before the protected work runs. `record_failure`/`record_event` (alias) and `reset(key)`. `client_ip(request)` uses only `request.client.host` — never an `X-Forwarded-For`-style header, since no reverse-proxy trust is configured anywhere in this app.

---

## backend/app/services/analyzer.py — PersonalityAnalyzer

10-question bank (Introduction → Hobbies → Career → Friends → Stress → Goals → Learning → Decision Making → Humor → Reflection). `finalize_analysis` flow: `CommunicationAnalyzer.analyze()` → `build_llm_prompt()` → `OllamaClient.chat(temp=0.2)` for the personality JSON → `parse_llm_response` (regex fallback if `json.loads` fails) → `build_identity_prompt()` → insert into `profiles_collection` (owned by the caller) and an empty `conversations_collection` document.

## backend/app/services/communication_analyzer.py — CommunicationAnalyzer

Pure-Python NLP fingerprint (no LLM): word frequency/favorite words, short forms, fillers, curse words, greetings, response-length style, repeated phrases, emoji usage, capitalization, punctuation, sentence statistics, paragraph style, typing habits, vocabulary richness. `build_llm_prompt()` asks Ollama for, per Big Five trait (openness/conscientiousness/extraversion/agreeableness/neuroticism), `{"score": 0-100, "description": "..."}`, plus `name`, `thinking_pattern`, `emotional_style`, `conversation_behaviour`, `interests`, `example_replies`, `summary`.

## backend/app/services/whatsapp_parser.py, whatsapp_import_service.py

`whatsapp_parser.py` parses a raw `.txt` WhatsApp export into `{sender, content, timestamp}` messages, skipping system/media/deleted-message lines, and raises `WhatsAppParseError` on unparseable input. `whatsapp_import_service.py` holds pending uploads in memory (`create_upload` → `upload_id`), and on `finalize_upload` runs the chosen sender's messages through the same `CommunicationAnalyzer` + `analyzer` pipeline the interview flow uses.

## backend/app/services/ollama_client.py — OllamaClient

```python
OLLAMA_HOST  = "http://localhost:11434"   # configurable
OLLAMA_MODEL = "mistral:7b-instruct-v0.3-q3_K_S"  # configurable
```

`chat(messages, stream=False, temperature=0.7, max_tokens=None, timeout=None) -> str` — non-streaming returns the full response; `stream=True` internally accumulates and still returns one string (used by `_fold_into_summary` and `ReflectService`). `stream_chat(messages, temperature=0.6, max_tokens=None) -> Iterator[str]` — yields individual tokens (used by `TextChatService.stream_chat` and `VoiceChatService.stream_turn`). Both raise `RuntimeError` on HTTP/connection errors, with host/model info in the message. `health_check() -> bool`.

| Call site | Temp | max_tokens |
|----------|------|------|
| `analyzer.generate_followup_question` | 0.5 | none |
| `analyzer.finalize_analysis` | 0.2 | none |
| `chat.py` text chat reply | 0.6 | 60 |
| `chat.py` `_fold_into_summary` | 0.3 | 200 |
| `voice_chat_service.stream_turn` | `VOICE_TEMPERATURE` (0.6) | `VOICE_MAX_TOKENS` (60) |
| `reflect_service.analyze` | 0.4 | 400 |

---

## MongoDB Schema

See [architecture.md](architecture.md#data-model) for the full collection shapes (`users`, `profiles`, `conversations`, `reflections`).

---

## Known Issues and Limitations

| Issue | Location | Notes |
|-------|----------|-------|
| In-memory session lookups + rate limiters | `analyzer.py`, `chat.py`, `voice_chat_service.py`, `rate_limiter.py`, `auth.py`'s `_pending_signups` | Lost on server restart. Not safe across multiple backend processes without a shared store (e.g. Redis). Profile/conversation/reflection data is unaffected — that's all in MongoDB. |
| `vapi-native` voice mode has no per-turn backend hook | `voice_chat_service.py` | This backend only learns what was said via the end-of-call webhook in that mode; the persisted summary is used by `custom-llm` mode only |
| Voice-only conversations don't advance the summary | `chat.py` (`_catch_up_summary` is only called from `TextChatService`) | Voice reads whatever summary exists but doesn't generate a new one on its own |
| `custom-llm` voice latency | `voice_chat_service.py` | CPU-only local Ollama TTFT can be several seconds to over a minute; not an issue in the default `vapi-native` mode |
| Existing profiles may lack Big Five scores | `communication_analyzer.py` | Profiles created before this schema existed need re-analysis to populate `personality.<trait>.score` |
| `PersonalityProfile` schema unused | `schemas.py` | Defined but no endpoint uses it as a `response_model` |
| Single default conversation thread | `twin_engine.py` (`thread="default"`) | `GET /api/profiles/:id/conversations` supports multiple threads architecturally; only `"default"` is ever created |
