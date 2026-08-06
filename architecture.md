# ReflectAI — Architecture Documentation

> **Purpose:** System design overview, data flow diagrams, API pipeline, AI architecture, and tech decisions for ReflectAI. Feed this file to any AI to understand HOW the system works end-to-end.
> **Last Updated:** 2026-08-06

---

## What is ReflectAI?

ReflectAI is an AI-powered "digital twin" platform. It interviews a user through 10 natural language questions, analyzes how they communicate (vocabulary, punctuation, emoji usage, sentence length, etc.), and uses a local LLM (Ollama) to build a personality profile. That profile is then used to create a chatbot that mimics the user's communication style — a "digital twin".

**Core value proposition:** Text chat LLM inference runs fully locally via Ollama. Voice chat uses Vapi (cloud) for speech-to-text and text-to-speech, but LLM inference runs locally too (unless switched to `vapi-native` mode). Note: profile data and conversation history are stored in MongoDB Atlas (cloud-hosted), not on the local machine — see [Data Model](#data-model).

**LLM:** Ollama running `mistral:7b-instruct-v0.3-q3_K_S` locally (configurable via `OLLAMA_MODEL` env var).

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        User's Machine                            │
│                                                                  │
│  ┌────────────┐   HTTP (port 5173)   ┌───────────────────────┐  │
│  │  Browser   │ ◄──────────────────► │  Vite Dev Server      │  │
│  │  (React)   │                      │  (frontend/)          │  │
│  └─────┬──────┘                      └───────────────────────┘  │
│        │ REST API calls (http://localhost:8000/api)              │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              FastAPI Backend (port 8000, v2.0.0)           │ │
│  │                                                             │ │
│  │  routers/                                                   │ │
│  │  ├── analyze.py       POST /api/analyze/*                  │ │
│  │  ├── chat.py          POST /api/chat/*                      │ │
│  │  ├── profiles.py      GET/DELETE /api/profiles/*            │ │
│  │  └── voice.py         GET/POST /api/voice/* + SSE stream   │ │
│  │                                                             │ │
│  │  services/                                                  │ │
│  │  ├── analyzer.py          PersonalityAnalyzer               │ │
│  │  ├── communication_analyzer.py  CommunicationAnalyzer       │ │
│  │  ├── twin_engine.py        DigitalTwinEngine (shared brain) │ │
│  │  ├── chat.py               TwinChat (text chat shim)        │ │
│  │  ├── voice_chat_service.py VoiceChatService (Vapi voice)    │ │
│  │  ├── vapi_client.py        VapiClient (webhook verification)│ │
│  │  └── ollama_client.py      OllamaClient (LLM HTTP wrapper)  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              MongoDB (app/database.py)                │  │ │
│  │  │  profiles       — one doc per twin (profile +        │  │ │
│  │  │                   metadata + interview transcript)   │  │ │
│  │  │  conversations  — one doc per chat thread (text +    │  │ │
│  │  │                   voice, shared)                     │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                         │                                        │
│  ┌──────────────────────▼────────────────────────────────┐      │
│  │           Ollama Server (port 11434)                   │      │
│  │           Model: mistral:7b-instruct-v0.3-q3_K_S      │      │
│  └───────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘

Voice Call (Vapi Cloud) — additional external path:
┌──────────────────────────────────────────────────────────────────┐
│  Browser (Vapi Web SDK)                                          │
│      ↓ WebRTC (audio)                                            │
│  Vapi Cloud ─────────── Deepgram STT ──────────────────────────  │
│      │ (if custom-llm)                                           │
│      └── POST /api/voice/llm/{session_id}/chat/completions       │
│              ↓ (through ngrok tunnel → localhost:8000)           │
│          FastAPI VoiceChatService → Ollama → SSE stream tokens   │
│              ↓                                                   │
│          Vapi TTS (Elliot voice) → Browser audio output          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Request Flow: Personality Analysis

### Phase 1: Start Analysis

```
Frontend (Analyze.jsx)
  → api.startAnalysis()
  → POST /api/analyze/start

Backend (routers/analyze.py)
  → analyzer.start_analysis()
  → PersonalityAnalyzer.create_session()
    → generates UUID session_id
    → initializes in-memory session: { messages: [], question_index: 0, ... }
  → Returns first question from question_bank[0]

Response: { session_id, message: "Hi! I'm ReflectAI..." }

Frontend
  → setSessionId, setQuestion, renders QuestionCard
```

### Phase 2: Question Loop (10+ turns)

```
Frontend (QuestionCard.jsx)
  → user types answer + clicks Submit
  → api.sendAnalysisMessage(sessionId, answerText)
  → POST /api/analyze/message

Backend (routers/analyze.py → analyzer.continue_analysis)
  1. receive_message → append user msg to session.messages
  2. CommunicationAnalyzer.analyze(session.messages) → fingerprint
  3. generate_followup_question → OllamaClient.chat(temp=0.5)
     → If OK: AI-generated contextual question
     → If Ollama fails: next_question from bank
  4. If bank exhausted → return { completed: True }
  5. Else: append question to session, return { completed: False, question, communication }

Backend (routers/analyze.py)
  → return { question, progress (0-100) }

Frontend
  → if progress >= 100: setIsCompleted(true)
  → else: update question + progress
```

### Phase 3: Finalize & Save

```
Frontend (Analyze.jsx finalization screen)
  → user enters profile name → api.finalizeAnalysis(sessionId, profileName)
  → POST /api/analyze/finalize

Backend (routers/analyze.py → analyzer.finalize_analysis)
  1. CommunicationAnalyzer.analyze(all messages) → full fingerprint
  2. CommunicationAnalyzer.build_llm_prompt → prompt for Ollama
  3. OllamaClient.chat(temp=0.2) → JSON personality analysis
  4. parse_llm_response → personality dict
  5. build_identity_prompt(communication, personality) → identity_prompt string
  6. merge_profile → { communication, llm_analysis, identity_prompt, ... }
  7. profile_id = uuid4()
  8. Write: profiles/{profile_id}/profile.json
  9. Write: profiles/{profile_id}/metadata.json
  10. Write: profiles/{profile_id}/conversation.json (interview transcript)
  11. Write: profiles/{profile_id}/conversations/default.json: { messages: [] }
  12. delete_session(session_id) — clean up memory
  → Return: { profile_id, profile }

Frontend (Analyze.jsx)
  → fetchProfiles() → selectProfile() → navigate('/dashboard')
```

---

## Request Flow: Twin Text Chat

```
User selects profile → navigates to /chat

Phase 1: Start Session
  api.startChat(profileId)
  → POST /api/chat/start { profile_id }

  Backend (TwinChat.create_session):
    → engine.build_system_messages(profile_id) → [identity_prompt, voice_grounding]
    → engine.load_history(profile_id) → existing conversation
    → engine.build_opening_line(profile_id) → instant greeting (no LLM call)
    → Update metadata.json last_used
    → return { session_id, message: <opening_line> }

Phase 2: Chat Loop
  api.sendChatMessage(sessionId, userMessage)
  → POST /api/chat/message { session_id, message }

  Backend (TwinChat.chat):
    1. engine.append_message(profile_id, "user", msg) → persist to disk
    2. engine.build_dynamic_context(last 5 user messages) → mood instruction
    3. engine.build_context_window(system_messages, history, dynamic_context)
       → [identity_prompt, voice_grounding, dynamic_context, ...last 20 msgs]
    4. OllamaClient.chat(messages, temperature=0.6, max_tokens=60)
    5. engine.append_message(profile_id, "assistant", reply) → persist to disk
    → return { reply }
```

---

## Request Flow: Twin Voice Chat (Vapi)

```
User navigates to /voice → Connect button clicked

Phase 1: Start Voice Session
  api.startVoiceSession(profileId)
  → POST /api/voice/start { profile_id }

  Backend (VoiceChatService.start_session):
    → engine.build_system_messages(profile_id)
    → engine.load_history(profile_id)
    → engine.build_opening_line(profile_id) → instant greeting
    → engine.append_message(profile_id, "assistant", opening_line, channel="voice")
       (opening line persisted to shared memory immediately)
    → build_assistant_config(session_id, opening_line):
       {
         voice: { provider: "vapi", voiceId: "Elliot" }
         transcriber: { provider: "deepgram", model: "nova-2" }
         firstMessage: <opening_line>
         silenceTimeoutSeconds: 180
         model: {
           provider: "custom-llm",
           url: "https://<ngrok>/api/voice/llm/{session_id}"
           -- OR --
           provider: "openai", model: "gpt-4o-mini"  (vapi-native mode)
         }
         server: { url: "https://<ngrok>/api/voice/webhook" }
       }
    → return { session_id, public_key, assistant: <config> }

Phase 2: Browser Starts Vapi Call
  useVapiCall hook:
    → new Vapi(public_key)
    → vapi.start(assistant_config)
    → Vapi Cloud: STT (Deepgram) + TTS (Elliot voice)
    → Browser: WebRTC audio

Phase 3: Per-Utterance Turn (custom-llm mode)
  Vapi Cloud calls:
  POST /api/voice/llm/{session_id}/chat/completions

  Backend (routers/voice.py → VoiceChatService.stream_turn):
    1. Extract latest user utterance from incoming_messages
    2. engine.append_message(profile_id, "user", utterance, channel="voice")
    3. engine.build_dynamic_context(last 5 user messages)
    4. engine.build_context_window(system_messages, history, dynamic_context)
    5. OllamaClient.stream_chat(messages, temperature=0.6, max_tokens=60)
    6. Each token → yield as OpenAI-compatible SSE chunk
    7. After stream complete: engine.append_message(profile_id, "assistant", full_reply)
    → StreamingResponse(media_type="text/event-stream")

  Vapi Cloud: receives token stream → converts to speech → plays to user

Phase 4: Call Lifecycle Webhooks
  Vapi Cloud calls POST /api/voice/webhook on:
    - status-update (in-progress) → mark_call_started
    - end-of-call-report → mark session ended

Phase 5: End Session
  Browser disconnect button → vapi.stop()
  api.endVoiceSession(sessionId) → POST /api/voice/end
  Backend: session["status"] = "ended"
```

---

## Voice Latency Analysis

Total per-turn latency budget (custom-llm mode):

| Stage | Owner | Typical Time |
|---|---|---|
| Deepgram STT | Vapi Cloud | ~200ms |
| Utterance detection (silence) | Vapi Cloud | ~300ms |
| ngrok tunnel round-trip | Network | ~50–150ms |
| Backend processing (context build) | FastAPI | ~10ms |
| **Ollama TTFT (local CPU)** | **Your machine** | **2,000–6,000ms** |
| Remaining token stream (60 tokens) | Ollama | ~500ms |
| Vapi TTS (Elliot) | Vapi Cloud | ~300ms |
| **Total** | | **~3–7 seconds** |

**Dominant bottleneck:** Local Ollama CPU inference Time-To-First-Token.

**Fix options:**
- `vapi-native` mode: uses gpt-4o-mini (~500ms total, not same Ollama engine)
- Smaller local model: phi3:mini, gemma2:2b (lower TTFT on CPU)
- Keep custom-llm + GPU hardware

---

## AI Pipeline Detail

### Two-Layer Analysis Architecture

```
Layer 1: Rule-Based (CommunicationAnalyzer)
┌────────────────────────────────────────────┐
│  WHAT IT MEASURES (15+ metrics):           │
│  • Word frequency & favorite words         │
│  • Internet short forms (idk, lol, etc.)   │
│  • Filler words (like, literally, etc.)    │
│  • Emoji usage + counts                    │
│  • Capitalization patterns (ratios)        │
│  • Punctuation frequency (!, ?, ., ...)    │
│  • Sentence length statistics              │
│  • Paragraph style                         │
│  • Greeting patterns (hi, hey, bro, etc.)  │
│  • Question asking frequency               │
│  • Repeated characters (loooool)           │
│  • Bigrams + trigrams (repeated phrases)   │
│  • Response length style (short/med/long)  │
│  • Vocabulary richness (type-token ratio)  │
│  • Typing habits (double spaces, ellipsis) │
└────────────────────────────────────────────┘

Layer 2: LLM-Based (Ollama)
┌────────────────────────────────────────────┐
│  WHAT IT INFERS (unmeasurable by rules):   │
│  • Big 5 personality traits                │
│    (openness, conscientiousness,           │
│     extraversion, agreeableness)           │
│  • Thinking patterns (logical, analytical) │
│  • Emotional style (reserved, formal)      │
│  • Conversation behaviour (polite, direct) │
│  • Interests + hobbies                     │
│  • Human-readable personality summary      │
└────────────────────────────────────────────┘

Combined Output → identity_prompt
┌────────────────────────────────────────────┐
│  Multi-paragraph system prompt injecting:  │
│  • All Layer 1 stats (writing style,       │
│    vocabulary, conversation patterns)      │
│  • All Layer 2 analysis (personality,      │
│    emotional style, interests)             │
│  • 15+ strict behavioral rules             │
│  • Verbatim interview quotes (voice        │
│    grounding message)                      │
│  Becomes the "soul" at every chat session  │
└────────────────────────────────────────────┘
```

### DigitalTwinEngine — Shared Brain

Both `TwinChat` (text) and `VoiceChatService` (voice) use the same `DigitalTwinEngine`. This is what makes text chat and voice chat the **same digital twin** rather than two separately-configured assistants.

```
DigitalTwinEngine
├── build_system_messages() → [identity_prompt_msg, voice_grounding_msg]
│     └── cached per profile_id (in-memory)
├── build_dynamic_context(recent_msgs) → mood-adaptation system msg
├── build_context_window(system, history, dynamic) → final message list for LLM
├── build_opening_line(profile_id) → instant greeting (no LLM call)
├── append_message(profile_id, role, content, channel) → persist + return updated history
└── load_history() / save_history() → conversations/default.json
```

### Context Window Strategy

```
Final message array sent to Ollama each turn:

[0] System: identity_prompt      ← ALWAYS included
[1] System: voice_grounding      ← ALWAYS included (verbatim interview quotes)
[2] System: dynamic_context      ← ALWAYS injected (mood adaptation, current turn)
[3..N] conversation history      ← CAPPED at last 20 items (MAX_HISTORY)

When conversation > 20: oldest messages dropped (sliding window)
System messages always stay. Twin "forgets" old chat but never forgets who it is.
```

### Dynamic Context Adaptation

Every turn, after reading the last 5 user messages:
- If user is excited → be more energetic
- If user is frustrated → speak more seriously
- If user is joking → joke back
- If user asks technical questions → be analytical

Does NOT change core writing style or personality — only mood/energy/flow.

---

## Data Model

### In-Memory Analysis Session
```python
sessions[uuid] = {
    created_at:   datetime,
    messages:     [{role, content}, ...],   # grows throughout interview
    question_index: 0-10,                   # current question
    completed:    bool,
    communication: dict | None,             # latest NLP fingerprint
    personality:  dict | None               # final merged profile (after finalize)
}
```

### In-Memory Voice Session (VoiceChatService)
```python
sessions[session_id] = {
    profile_id:      str,           # UUID for file operations
    system_messages: list,          # [identity_prompt, voice_grounding]
    history:         list,          # shared conversation (same as text chat)
    status:          str,           # created | active | ended
    started_at:      float,         # time.time()
    call_id:         str | None,    # Vapi call ID (from webhook)
    ended_at:        float | None   # time.time() on end
}
```

### MongoDB Collections

`profiles` collection — one document per twin, `_id` = profile UUID:
```
{
  _id            ← profile UUID
  name           ← user-given profile name
  created_at     ← ISO datetime
  last_used      ← ISO datetime (updated on each chat/voice session)
  version        ← 1 (int)
  profile:
    ├── communication           ← CommunicationAnalyzer output
    │   ├── statistics
    │   ├── vocabulary
    │   ├── conversation_style
    │   ├── writing_style
    │   └── writing_patterns
    ├── llm_analysis            ← Ollama's personality JSON
    │   ├── personality         ← Big 5 traits with levels
    │   ├── thinking_pattern
    │   ├── emotional_style
    │   ├── conversation_behaviour
    │   ├── interests           ← string array
    │   └── summary             ← human-readable text
    ├── identity_prompt         ← Full system prompt string
    ├── generated_by            ← "ReflectAI"
    └── version                 ← "1.0"
  conversation   ← verbatim interview transcript (source material)
                   [{role, content}, ...]
}
```

`conversations` collection — one document per chat thread, `_id` =
`"{profile_id}:{thread}"`, shared by text + voice:
```
{
  _id          ← "{profile_id}:default"
  profile_id   ← profile UUID
  thread       ← "default"
  messages     ← [{role, content, channel: "text"|"voice"}, ...]
  updated_at   ← ISO datetime
}
```

---

## Component Dependency Map

### Backend Dependencies
```
main.py (v2.0.0)
├── routers/analyze.py
│   └── services/analyzer.py
│       ├── services/communication_analyzer.py
│       └── services/ollama_client.py
├── routers/chat.py
│   └── services/chat.py (TwinChat)
│       └── services/twin_engine.py (DigitalTwinEngine)
│           └── services/ollama_client.py
├── routers/profiles.py
│   └── (reads MongoDB profiles/conversations collections directly)
└── routers/voice.py
    └── services/voice_chat_service.py
        ├── services/twin_engine.py (DigitalTwinEngine — shared)
        ├── services/ollama_client.py
        └── services/vapi_client.py
```

### Frontend Dependencies
```
App.jsx
├── provides: ProfileProvider (ProfileContext.jsx)
│             └── uses: api.js (getProfiles, deleteProfile)
└── routes to pages:
    ├── Landing.jsx
    ├── Analyze.jsx
    │   ├── uses: QuestionCard, ProgressCard, AnalysisSidebar
    │   └── uses: api.js (startAnalysis, sendAnalysisMessage, finalizeAnalysis)
    ├── Profiles.jsx
    │   └── uses: ProfileGrid → ProfileCard
    ├── Dashboard.jsx
    │   └── uses: PersonalityCard, StatCard
    ├── ModeSelect.jsx   (Chat/Voice mode hub)
    ├── Chat.jsx
    │   ├── uses: MessageList → ChatBubble, TypingIndicator, ChatInput
    │   └── uses: api.js (startChat, sendChatMessage)
    ├── Voice.jsx
    │   ├── uses: SpeakingIndicator, WaveformVisualizer, VoiceTranscript, CallTimer, ConnectionStatus
    │   ├── uses: useVapiCall hook
    │   └── uses: api.js (getVoiceConfig, startVoiceSession, endVoiceSession)
    └── Reflect.jsx (stub)
```

---

## API Contract Summary

All endpoints at `http://localhost:8000/api`

```
POST /api/analyze/start              → { session_id, message }
POST /api/analyze/message            → { question, progress }
POST /api/analyze/finalize           → { profile_id, profile }

POST /api/chat/start                 → { session_id, message }
POST /api/chat/message               → { reply }

GET  /api/profiles                   → [{ id, name, created_at, last_used, conversation_count }]
GET  /api/profiles/:id               → { metadata, profile }
DELETE /api/profiles/:id             → { success, message }
GET  /api/profiles/:id/conversations → [{ id, title, message_count, updated_at }]

GET  /api/voice/config               → { enabled, public_key, llm_provider, reason }
POST /api/voice/start                → { session_id, public_key, assistant: <VapiAssistantConfig> }
POST /api/voice/end                  → { session_id, status, duration_seconds }
GET  /api/voice/session/:id          → { session_id, status, duration_seconds }
POST /api/voice/webhook              → { received, type }   (called by Vapi Cloud)
POST /api/voice/llm/:id/chat/completions → SSE stream of OpenAI-compat chunks (called by Vapi Cloud)
```

FastAPI auto-generates interactive docs at: `http://localhost:8000/docs`

---

## Tech Decisions and Rationale

| Decision | Why |
|----------|-----|
| Local Ollama instead of OpenAI API | Privacy-first: no data leaves machine for text chat |
| DigitalTwinEngine shared by text + voice | Single source of truth for personality; prevents drift between channels |
| Vapi for voice | Real-time WebRTC, high-quality STT/TTS; we focus on personality, not telephony |
| custom-llm Vapi mode (default) | Uses same Ollama twin for voice — voice and text chat are the same twin |
| vapi-native mode option | Faster fallback when CPU Ollama is too slow for real-time voice |
| ngrok tunnel for custom-llm | Vapi cloud can't reach localhost; tunnel bridges cloud → local |
| MongoDB storage | Profiles + conversation history survive crashes/restarts; connection pooling keeps reads/writes fast |
| React Context for profiles | Avoids prop drilling; localStorage sync preserves selection across refreshes |
| Router-based backend (v2.0.0) | Separates concerns; each feature area has its own router file |
| Rolling context window (20 msgs) | Keeps LLM token count bounded and predictable |
| Two-layer AI pipeline | Rule-based = fast + deterministic; LLM = semantic depth |
| Per-turn MongoDB persistence | Chat history survives backend restarts (resilient by design) |

---

## Current Limitations and Planned Extensions

### Active Limitations
| Limitation | Impact | Fix |
|------------|--------|-----|
| In-memory session lookups | Active interview/chat/voice sessions (not profile or conversation data, which now live in MongoDB) are lost on server restart | SQLite or Redis for session state |
| Voice TTFT ~3-7s | Poor UX in voice conversations | vapi-native mode or faster model |
| Non-streaming text chat | Reply appears all at once | SSE or WebSocket streaming |
| No auth | Anyone on port 8000 can access all profiles | JWT auth |
| Single default conversation | One chat thread per profile | Multi-conversation routing |
| Reflect page is stub | Feature not designed | Design + implement journaling |

### Feature Roadmap
1. **Streaming text chat** — OllamaClient.stream_chat() already implemented, needs wiring to chat endpoint + frontend EventSource
2. **Voice latency fix** — switch to `vapi-native` or faster local model
3. **Session-state persistence** — SQLite/Redis so in-progress interview/chat/voice sessions also survive a restart (profile + conversation data is already persisted in MongoDB)
4. **Conversation summarization** — `TwinChat.summarize_conversation()` is a stub
5. **Multiple conversations** — `GET /api/profiles/:id/conversations` endpoint already built
6. **Reflect feature** — journaling + mood tracking
7. **Per-profile voice selection** — different Vapi voice per twin (architecture ready in config)
