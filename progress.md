# ReflectAI — Project Progress & Work Remaining

> **Purpose:** Honest audit of what is built, what is a stub, what is missing, and what needs to be done next. Feed this to any AI to understand the current state before planning new features.
> **Last Updated:** 2026-09-04

---

## Overall Completion

| Area | Status | Notes |
|------|--------|-------|
| Backend API (core) | Complete | Router-based architecture; routers for auth, analyze, chat, voice, profiles, reflect |
| Backend — Auth | Complete | Email/password (OTP-verified signup) + Google Sign-In, session cookie, login rate limiting, account-enumeration protection on login and signup |
| Backend — Analyze | Complete | 10-question interview flow, profiles saved to MongoDB |
| Backend — WhatsApp import | Complete | Upload → parse → pick sender → finalize into a profile; size-limited and chunk-read |
| Backend — Chat (text) | Complete | `TextChatService`, SSE streaming, conversation summarization |
| Backend — Voice (Vapi) | Complete | `vapi-native` (default) and `custom-llm` (fallback) modes, webhook handling, session lifecycle |
| Backend — Reflect | Complete | `ReflectService` + `reflect.py` router — CRUD + AI reflection, ownership-scoped |
| Backend — Personality (Big Five) | Complete | LLM prompt asks for openness/conscientiousness/extraversion/agreeableness/neuroticism, 0–100 score + description each |
| Frontend — Landing Page | Complete | Marketing homepage |
| Frontend — Auth Pages | Complete | Login.jsx, Signup.jsx (OTP step), Google Sign-In button, `AuthContext`, `ProtectedRoute` |
| Frontend — Analyze Flow | Complete | Interview flow + WhatsApp import flow, both end at profile creation |
| Frontend — Profiles Page | Complete | Grid of profile cards, active-twin banner, delete |
| Frontend — Dashboard | Complete | Stats, Big Five bar + radar chart visualization, conversation history |
| Frontend — Chat Page | Complete | Streaming replies (progressive token rendering), full history |
| Frontend — Voice Page | Complete | Full Vapi call integration with waveform, transcript, timer |
| Frontend — Reflect Page | Complete | Real journaling UI: compose, save, AI reflection, history, detail view, edit, delete |
| Frontend — ModeSelect Page | Complete | Mode hub between Chat and Voice, at `/mode` |
| Frontend — blur/performance | Complete | Repeated cards (`Card.jsx` and its consumers, `ChatBubble`, `TypingIndicator`) no longer use `backdrop-blur`; kept only on single/limited elements (Navbar, Modal, Loader, main panels) |
| Data Persistence | Complete | MongoDB (Atlas or self-hosted) — `profiles`, `conversations`, `users`, `reflections` collections. No file-based storage. |
| Conversation summarization | Complete | Older turns are folded into an AI-generated summary once history exceeds the 20-message window; summary is injected into future LLM context |

---

## What Is DONE (Built and Working)

### Backend

#### Authentication (routers/auth.py, services/auth_service.py, email_service.py, rate_limiter.py) — COMPLETE
- [x] Email/password signup with OTP email verification (`POST /api/auth/signup/request-otp` → `POST /api/auth/signup/verify-otp`)
- [x] Google Sign-In (`POST /api/auth/google`, verifies the Google ID token server-side)
- [x] Login (`POST /api/auth/login`) — bcrypt password verification, httpOnly session cookie (JWT)
- [x] Login rate limiting — 5 failed attempts / 15-minute window per client IP, `429` + `Retry-After` on exceeding it, resets on success
- [x] Login account-enumeration protection — nonexistent email, wrong password, and Google-only accounts all get an identical response (status, body, and near-identical timing via a dummy bcrypt check)
- [x] Signup email-enumeration protection — `signup/request-otp` returns the same generic response whether the email is new, already registered, or on resend cooldown; a dummy SMTP round-trip equalizes timing with a real send
- [x] Signup OTP request rate limiting — same mechanism as login, separate counter
- [x] `GET /api/auth/me`, `POST /api/auth/logout`
- [x] Every profile/conversation/reflection-scoped route checks `owner_id` against the authenticated user

#### PersonalityAnalyzer (services/analyzer.py) — COMPLETE
- [x] Session creation and management (in-memory, per logged-in user)
- [x] 10-question bank
- [x] AI-driven follow-up question generation (Ollama), falls back to the question bank if Ollama fails
- [x] Final personality analysis (Big Five traits with 0–100 score + description each, thinking pattern, emotional style, interests, summary)
- [x] Identity prompt builder
- [x] Profile saved to MongoDB `profiles` collection, owned by the signed-in user

#### WhatsApp Import (services/whatsapp_import_service.py, whatsapp_parser.py) — COMPLETE
- [x] `.txt` WhatsApp export parsing, participant/message-count detection
- [x] Upload size capped (`MAX_WHATSAPP_UPLOAD_SIZE_MB`, default 15MB) — enforced via bounded chunked reads, so an oversized file is rejected (`413`) before being fully read into memory or reaching the parser
- [x] Finalize step picks the target sender and builds a profile through the same analysis pipeline as the interview flow

#### CommunicationAnalyzer (services/communication_analyzer.py) — COMPLETE
- [x] 15+ rule-based communication metrics (word frequency, fillers, emoji, capitalization, punctuation, sentence stats, etc.)
- [x] LLM prompt builder that asks for Big Five personality scores + description, thinking pattern, emotional style, interests, summary

#### OllamaClient (services/ollama_client.py) — COMPLETE
- [x] Non-streaming `chat()` and token-by-token `stream_chat()`
- [x] `health_check()`, configurable host/model

#### DigitalTwinEngine (services/twin_engine.py) — COMPLETE
- [x] Shared "brain" for Text Chat and Voice Chat
- [x] Loads profile + conversation memory from MongoDB, builds `TwinContext`
- [x] `build_dynamic_context()` — mood adaptation from the last 5 user messages
- [x] `build_opening_line()` — instant greeting, no LLM call
- [x] `load_history()` / `save_history()` / `append_message()` — persistent shared conversation memory (MongoDB `conversations` collection)
- [x] `get_summary_state()` / `save_summary_state()` — persisted running conversation summary + `summarized_through` cursor
- [x] `build_context_window()` — system messages + optional summary + optional dynamic context + last `MAX_HISTORY` (20) turns

#### TextChatService (services/chat.py) — COMPLETE
- [x] Session creation (loads profile + history via engine)
- [x] `chat()` — non-streaming turn, returns the full reply
- [x] `stream_chat()` — SSE-friendly turn, yields tokens as Ollama generates them
- [x] Conversation summarization — `_catch_up_summary()` runs every turn, folding messages that have fallen outside the recent window into a running AI-generated summary; `summarize_conversation()` is an on-demand "summarize everything so far" action
- [x] Summarization never breaks a chat turn on failure — falls back to the last known-good summary (or none) and logs the failure

#### VoiceChatService (services/voice_chat_service.py) — COMPLETE
- [x] `start_session()` — creates session, loads twin memory, builds Vapi assistant config
- [x] Two LLM modes via `VAPI_LLM_PROVIDER`:
  - `vapi-native` (default) — Vapi's own hosted model (a free OpenRouter model by default) generates every reply; fast enough for a live call
  - `custom-llm` — Vapi calls back into this backend's own Ollama per utterance; kept working as a local-only fallback, but slow on CPU
- [x] `stream_turn()` (custom-llm mode) — rebuilds context (including the persisted summary, if any) and streams Ollama tokens back per utterance
- [x] `handle_webhook_event()` — call lifecycle + (`vapi-native` mode) transcript sync from the end-of-call report
- [x] Shared conversation memory with Text Chat

#### Reflect / Journaling (routers/reflect.py, services/reflect_service.py) — COMPLETE
- [x] `POST /api/reflect` — create entry, kicks off AI analysis immediately, entry is saved even if analysis fails
- [x] `GET /api/reflect`, `GET /api/reflect/{id}` — list (paginated) and fetch, always owner-scoped
- [x] `PATCH /api/reflect/{id}` — edit, clears the stale analysis and re-runs it against the new text
- [x] `POST /api/reflect/{id}/analyze` — re-run analysis (the "try again" action after a failure)
- [x] `DELETE /api/reflect/{id}`
- [x] AI analysis returns mood (Positive/Negative/Neutral/Mixed), themes, a reflection, observations, and a next step — parsed from Ollama's JSON output with a fenced-code-block fallback
- [x] Analysis failure never loses the journal entry — it's saved first, `analysis.status` becomes `"failed"` if the AI call fails

#### Config (config.py) — COMPLETE
- [x] Ollama, MongoDB, Auth (JWT/Google/cookie/rate-limit), Email/OTP, WhatsApp upload, Vapi settings — all centralized with sane defaults

#### API Endpoints — see [backend.md](backend.md) for the full, current list (auth, analyze, WhatsApp import, chat, profiles, reflect, voice)

---

### Frontend

#### Auth — COMPLETE
- [x] `Login.jsx`, `Signup.jsx` (with OTP entry step), Google Sign-In button
- [x] `AuthContext` — current user, `authLoading`, login/signup/logout/Google methods
- [x] `ProtectedRoute` — redirects to `/login` when not authenticated; every twin/reflect/chat/voice route is wrapped in it

#### Common Components — COMPLETE
- [x] Button, Card (repeated-card blur removed — see [progress note above](#overall-completion)), Input, Loader, Modal, Navbar, ProtectedRoute

#### Analysis Feature Components — COMPLETE
- [x] ProgressCard, QuestionCard, AnalysisSidebar

#### Profile Feature Components — COMPLETE
- [x] ProfileCard, ProfileGrid, PersonalityCard, StatCard, `PersonalityChart` (Big Five bar chart + radar chart, normalizes 0–1 vs 0–100 vs string vs `{score, description}` input shapes, shows "N/A" for missing traits)

#### Chat Feature Components — COMPLETE
- [x] ChatBubble (streaming-aware), ChatInput, MessageList, TypingIndicator

#### Voice Feature Components — COMPLETE
- [x] CallTimer, ConnectionStatus, SpeakingIndicator, VoiceTranscript, WaveformVisualizer, `useVapiCall` hook

#### Reflect Feature Components — COMPLETE
- [x] `ReflectEntryCard` (history list item with mood badge), `ReflectDetailModal` (original entry + AI reflection, edit, delete)

#### Pages — ALL BUILT

Landing.jsx — DONE — hero, features, how it works, technology, pricing, footer, simulated demo chat widget (hardcoded responses, not connected to the real API — cosmetic only)

Login.jsx / Signup.jsx — DONE — email/password + Google Sign-In; Signup includes the OTP-entry step

Analyze.jsx — DONE — full 10-question interview flow, **plus** a WhatsApp chat import flow (upload → pick sender → finalize) as an alternative path to creating a profile

Profiles.jsx — DONE — profile grid, active twin banner, delete with confirm modal

Dashboard.jsx — DONE — profile stats, Big Five personality visualization (bar chart + radar chart), conversation history, quick actions

Chat.jsx — DONE — full chat UI, **streams replies progressively** (SSE), falls back to non-streaming JSON automatically if the client doesn't request `text/event-stream`

Voice.jsx — DONE — Vapi SDK integration, connect/disconnect, live transcript, waveform

Reflect.jsx — DONE — compose box, save-and-reflect flow, history list, detail modal, edit, delete, re-analyze on failure

ModeSelect.jsx — DONE — mode hub between Chat and Voice, mounted at `/mode`

---

## What Is NOT DONE / Known Limitations

These are current, verified limitations — not stale claims:

- **In-memory session/rate-limiter state.** Active interview/chat/voice sessions and the login/OTP rate limiters live in per-process memory, not MongoDB. They reset on a backend restart, and if this backend is ever run as more than one process/instance, each instance would track its own separate counters/sessions — a shared store (e.g. Redis) would be needed for horizontal scaling. Profile, conversation, and reflection *data* is unaffected — that's all in MongoDB.
- **Existing profiles may need re-analysis for Big Five scores.** Profiles created before the personality-visualization work was done don't have `personality.<trait>.score` populated — the Dashboard shows "Personality insights aren't available yet" for those until the profile is re-analyzed (a new interview or WhatsApp import). This is not automatic/retroactive.
- **`vapi-native` voice mode doesn't share this backend's live turn-by-turn context the way `custom-llm` does.** In `vapi-native` mode, Vapi's own hosted model generates replies using a system prompt built once at call start; this backend only learns what was actually said via the end-of-call webhook, not per-turn. `custom-llm` mode (the fallback) does read the persisted conversation summary on every turn.
- **A voice-only conversation doesn't advance the conversation summary on its own** — only `TextChatService` runs the summarization/folding step. Voice (`custom-llm` mode) reads whatever summary already exists but won't generate a new one unless the same conversation is also used from Text Chat.
- **Voice latency in `custom-llm` mode** — a CPU-only local Ollama model's time-to-first-token can be several seconds to over a minute; `vapi-native` (the default) doesn't have this problem since it uses a hosted model.
- **Landing page's demo chat widget is cosmetic** — hardcoded responses, not wired to the real backend.
- **No profile rename functionality.**
- **Navbar anchor links** (`#features`, etc.) only scroll correctly on the Landing page — they appear on every page since Navbar is shared.

---

## File Status Quick Reference

See [backend.md](backend.md) and [frontend.md](frontend.md) for the full current file-by-file reference — kept there instead of duplicated here so there's one place to update per change.
