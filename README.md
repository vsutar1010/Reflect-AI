# ReflectAI

ReflectAI builds a **digital twin** of a real person from a short interview, then lets you talk to that twin — by text or by live voice call — in a way that actually sounds like them: their vocabulary, sentence length, slang, humor, and habits, not a generic assistant wearing their name.

Everything runs on your own machine by default (local LLM via [Ollama](https://ollama.com)). Voice calls additionally use [Vapi](https://vapi.ai) for real-time speech, because a local CPU model is too slow for a live conversation — see [Architecture](#architecture) for why that's not a contradiction.

---

## Table of Contents

- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Setup guide](#setup-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Ollama (required)](#2-ollama-required)
  - [3. Backend](#3-backend)
  - [4. Frontend](#4-frontend)
  - [5. Run it (text chat only)](#5-run-it-text-chat-only)
  - [6. Voice chat setup (optional)](#6-voice-chat-setup-optional)
- [Configuration reference](#configuration-reference)
- [Where to change things](#where-to-change-things)
- [Troubleshooting](#troubleshooting)

---

## How it works

```
1. Analysis         Answer 10 questions. ReflectAI studies HOW you write —
                     vocabulary, punctuation, sentence length, slang, emoji
                     use, humor — not just what you say.

2. Profile           A personality profile + your verbatim answers are
   created            saved to disk (profiles/{id}/).

3. Choose mode        Talk to the twin by Text Chat or Voice Chat — your
                       pick, same twin either way.

4. Talk to your twin   Text runs on your local Ollama model. Voice runs in
                        real time via Vapi. Both draw from the exact same
                        analyzed profile and share one conversation memory
                        — say something on a call, see it in the text
                        thread a moment later, and vice versa.
```

## Architecture

The core rule the whole backend is built around: **one analyzed personality, pluggable execution engine.** Text Chat and Voice Chat are allowed to use completely different LLMs (a local model vs. a hosted one) — what they may never do is diverge in *who the person is*, because both are built from the same source data through the same code path.

```
                    Analysis (10-question interview)
                                 │
                                 ▼
                profile.json  +  conversation.json
           (derived personality)   (verbatim answers)
                                 │
                                 ▼
                        DigitalTwinEngine
        loads profile + conversation + memory, and produces:
                                 │
                            TwinContext
              (plain data — identity, real quotes, traits,
               interests — no knowledge of any LLM provider)
                                 │
                  ┌──────────────┴──────────────┐
                  ▼                              ▼
          OllamaPromptAdapter             VapiPromptAdapter
        (verbose, repetitive —          (concise, distilled —
         a small local model needs       a strong hosted model
         heavy repetition to             needs far less hand-
         follow instructions)            holding, and is framed
                  │                      for spoken conversation,
                  ▼                      not texting)
           TextChatService                       │
           talks to Ollama                        ▼
                  │                        VoiceChatService
                  │                    configures a Vapi assistant,
                  │                    handles call lifecycle + webhooks
                  │                              │
                  └────────── Shared Memory ─────┘
                     conversations/default.json
              (every turn tagged "text" or "voice" so
               either channel can pick up mid-conversation)
```

**Why voice doesn't use Ollama by default:** a CPU-only local model's time-to-first-token was measured at 10–90+ seconds during development — unusable for a live phone call. Voice instead runs on Vapi's hosted model (configurable — see [Voice chat setup](#6-voice-chat-setup-optional)), while a **custom-llm fallback mode** that does route voice through your local Ollama is kept fully working for privacy-sensitive or fully-offline use — just expect long pauses in that mode.

### Backend layout

| Layer | File | Responsibility |
|---|---|---|
| Engine | `app/services/twin_engine.py` | Loads profile + conversation + memory. Produces `TwinContext`. Knows nothing about Ollama or Vapi. |
| Data | `app/services/twin_context.py` | The plain-data bundle every adapter builds from. |
| Adapters | `app/adapters/ollama_adapter.py`, `vapi_adapter.py` | Pure functions: `TwinContext` → provider-shaped prompt. |
| Text channel | `app/services/chat.py` (`TextChatService`) | Talks to Ollama. |
| Voice channel | `app/services/voice_chat_service.py` (`VoiceChatService`) | Configures Vapi, handles call lifecycle + webhook-based memory sync. |
| Analysis | `app/services/analyzer.py`, `communication_analyzer.py` | The 10-question interview → personality profile pipeline. |
| Routers | `app/routers/*.py` | FastAPI endpoints, thin — delegate to the services above. |

Neither `TextChatService` nor `VoiceChatService` contains any personality logic — they only decide *which* adapter to call and wire the result into their transport. All prompt content lives in `app/adapters/`.

## Project structure

```
REFLECT/
├── backend/
│   ├── app/
│   │   ├── adapters/          # OllamaPromptAdapter, VapiPromptAdapter
│   │   ├── routers/           # analyze, chat, voice, profiles (FastAPI)
│   │   ├── services/          # engine, analyzer, chat services, ollama/vapi clients
│   │   ├── config.py          # all environment configuration, one place
│   │   ├── dependencies.py    # shared service singletons
│   │   ├── main.py            # FastAPI app + router registration
│   │   └── schemas.py         # Pydantic request/response models
│   ├── profiles/              # generated digital twins (gitignored)
│   ├── .env                   # your real config (gitignored, never commit)
│   ├── .env.example           # template — copy this to .env
│   ├── requirements.txt
│   └── run.py                 # entry point: python run.py
└── frontend/
    ├── src/
    │   ├── pages/              # Landing, Analyze, Profiles, Dashboard, ModeSelect, Chat, Voice
    │   ├── components/         # common/ (Button, Card...) + features/ (chat/, voice/, profile/, analysis/)
    │   ├── hooks/               # useVapiCall.js
    │   ├── context/             # ProfileContext (selected twin, persisted)
    │   └── services/api.js      # all backend API calls
    └── package.json
```

## Setup guide

### 1. Prerequisites

- **Python 3.11+** with [conda](https://docs.conda.io/) (this project was built and tested using a conda environment named `reflectai`)
- **Node.js 18+** and npm
- **[Ollama](https://ollama.com/download)** installed and running locally
- A modern browser with microphone access (for Voice Chat)

Voice Chat additionally needs a free [Vapi](https://vapi.ai) account and a tunneling tool (covered in [step 6](#6-voice-chat-setup-optional)) — but the whole app, including Text Chat and the analysis interview, works without any of that. Set voice up later if you just want to try it first.

### 2. Ollama (required)

1. Install Ollama from [ollama.com/download](https://ollama.com/download).
2. Pull a model. The project defaults to a small quantized model that runs on CPU:
   ```bash
   ollama pull mistral:7b-instruct-v0.3-q3_K_S
   ```
   Any Ollama-compatible chat model works — bigger/better models give better personality analysis and text chat quality, at the cost of speed. See [Where to change things](#where-to-change-things) to use a different one.
3. Make sure Ollama is running before you start the backend:
   ```bash
   ollama serve
   ```
   (On Windows, the Ollama desktop app runs this for you in the background automatically once installed.)

### 3. Backend

```bash
cd backend

# Create and activate the conda environment (name it whatever you like —
# this project's own dev environment is called "reflectai")
conda create -n reflectai python=3.11 -y
conda activate reflectai

pip install -r requirements.txt

# Copy the config template and open it
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

Open `backend/.env` and set at minimum:
```env
OLLAMA_MODEL=mistral:7b-instruct-v0.3-q3_K_S
```
Everything else in `.env` is only needed for Voice Chat — leave the rest as-is for now. Full reference in [Configuration reference](#configuration-reference).

### 4. Frontend

```bash
cd frontend
npm install
```

No `.env` is required on the frontend for Text Chat — it talks to the backend at `http://localhost:8000` by default.

### 5. Run it (text chat only)

Two terminals:

```bash
# Terminal 1 — backend
cd backend
conda activate reflectai
python run.py
```

```bash
# Terminal 2 — frontend
cd frontend
npm run dev
```

Open **http://localhost:5173**, click **Create Twin**, answer the 10 questions, then pick **Text Chat**. Voice Chat will show a clear "not configured yet" screen with a link back to Text Chat until you complete step 6.

### 6. Voice chat setup (optional)

Voice Chat needs three things: a public URL for this backend, a Vapi account, and an LLM provider for Vapi to use (a free one is fine — this is what makes the voice replies fast, unlike your local Ollama model).

#### 6a. Install a tunnel (ngrok)

Vapi is a cloud service — it cannot reach `http://localhost:8000` on your machine. A tunnel gives your local backend a temporary public URL.

**Windows — via Microsoft Store (easiest, no PATH setup):**
1. Open the **Microsoft Store** app.
2. Search for **"ngrok"** and install it.
3. Open a terminal and run `ngrok` once to confirm it's on your PATH — if the Store install doesn't add it automatically, open the ngrok app once from the Start menu, which registers it.
4. Sign up for a free ngrok account at [ngrok.com](https://ngrok.com), then run the auth command it gives you (one time):
   ```bash
   ngrok config add-authtoken YOUR_TOKEN_HERE
   ```

**Alternative (any platform) — via winget:**
```bash
winget install ngrok.ngrok
```

**Alternative — via package manager:** `brew install ngrok` (macOS) or download directly from [ngrok.com/download](https://ngrok.com/download).

With the backend already running on port 8000 (step 5), open a **third terminal**:
```bash
ngrok http 8000
```
ngrok prints a line like:
```
Forwarding    https://abcd-1234.ngrok-free.app -> http://localhost:8000
```
Copy that `https://...ngrok-free.app` URL — you'll need it in the next step. **This URL changes every time you restart ngrok** on the free plan, so you'll need to update `.env` again after any restart.

#### 6b. Vapi account + keys

1. Sign up at [vapi.ai](https://vapi.ai) (free tier is enough to test).
2. In the Vapi dashboard, go to **API Keys** and copy your **Public Key** and **Private Key**.
3. In `backend/.env`, set:
   ```env
   PUBLIC_BACKEND_URL=https://abcd-1234.ngrok-free.app   # from step 6a, no trailing slash
   VAPI_PUBLIC_KEY=your-public-key
   VAPI_PRIVATE_KEY=your-private-key
   ```

#### 6c. A free model provider for Vapi (OpenRouter)

Vapi needs an actual LLM to generate voice replies in real time. `gpt-4o-mini` (OpenAI) works but costs money. **OpenRouter** offers genuinely free models (their model IDs end in `:free`) with no card required:

1. Sign up at [openrouter.ai](https://openrouter.ai) and create an API key under **Keys**.
2. In your **Vapi dashboard**, go to **Provider Credentials** (sometimes called **Credentials** or **API Keys** depending on the dashboard version) and add a new **OpenRouter** credential using that key. This is a one-time setup step *in Vapi's dashboard* — nothing to configure in this repo for it.
3. Pick a currently-free model from [openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0) — the free catalog **rotates over time**, so don't assume any specific ID stays available forever. Prefer a small instruct model (Llama/Gemma/Qwen/Mistral `*-instruct:free` variants) for quick, natural replies; avoid huge 70B+ models, which are slower.
4. In `backend/.env`:
   ```env
   VAPI_LLM_PROVIDER=vapi-native
   VAPI_NATIVE_MODEL_PROVIDER=openrouter
   VAPI_NATIVE_MODEL=google/gemma-4-26b-a4b-it:free   # whatever you picked in step 3
   ```

Other providers work identically if you'd rather use them (also configured as a Provider Credential in Vapi's dashboard first):
- `VAPI_NATIVE_MODEL_PROVIDER=google` + `VAPI_NATIVE_MODEL=gemini-2.0-flash` — free tier via Google AI Studio, no card required in most regions.
- `VAPI_NATIVE_MODEL_PROVIDER=groq` + `VAPI_NATIVE_MODEL=llama-3.1-8b-instant` — free and extremely fast, *if* Groq appears as an option in your Vapi account (it isn't available in every account).
- `VAPI_NATIVE_MODEL_PROVIDER=openai` + `VAPI_NATIVE_MODEL=gpt-4o-mini` — not free, but reliable if you don't mind the small cost.

#### 6d. Restart everything

```env
# backend/.env should now have at least:
PUBLIC_BACKEND_URL=https://abcd-1234.ngrok-free.app
VAPI_PUBLIC_KEY=...
VAPI_PRIVATE_KEY=...
VAPI_LLM_PROVIDER=vapi-native
VAPI_NATIVE_MODEL_PROVIDER=openrouter
VAPI_NATIVE_MODEL=...:free
```

Stop and restart the backend (`Ctrl+C`, then `python run.py` again — config is only read on startup). Open the app, select a twin, choose **Voice Chat** — it should now show a live Connect button instead of the "not configured" screen.

**Every time ngrok restarts**, its URL changes: update `PUBLIC_BACKEND_URL` in `.env` and restart the backend again. (A paid ngrok plan gets you a fixed subdomain if this gets tedious.)

## Configuration reference

All of this lives in `backend/.env` — see `backend/.env.example` for the full, commented template.

| Variable | Used for | Notes |
|---|---|---|
| `OLLAMA_HOST` | Analysis, Text Chat, custom-llm voice | Default `http://localhost:11434` |
| `OLLAMA_MODEL` | Analysis, Text Chat, custom-llm voice | Any model you've pulled with `ollama pull` |
| `PUBLIC_BACKEND_URL` | Voice Chat (both modes) | Your ngrok/tunnel URL, no trailing slash |
| `VAPI_PUBLIC_KEY` | Voice Chat | From Vapi dashboard → API Keys |
| `VAPI_PRIVATE_KEY` | Voice Chat (optional) | Only needed for server-side REST calls, not required for basic use |
| `VAPI_SERVER_SECRET` | Voice Chat (optional) | Any random string; verifies webhook/custom-llm requests actually came from Vapi |
| `VAPI_VOICE_PROVIDER` / `VAPI_VOICE_ID` | Voice Chat | Text-to-speech voice, default `vapi` / `Elliot` |
| `VAPI_TRANSCRIBER_*` | Voice Chat | Speech-to-text provider/model/language, default Deepgram `nova-2` |
| `VAPI_LLM_PROVIDER` | Voice Chat | `vapi-native` (fast, default) or `custom-llm` (local Ollama, slow) |
| `VAPI_NATIVE_MODEL_PROVIDER` / `VAPI_NATIVE_MODEL` | Voice Chat, vapi-native mode | Which hosted model Vapi uses — see [6c](#6c-a-free-model-provider-for-vapi-openrouter) |
| `VAPI_CUSTOM_LLM_TIMEOUT_SECONDS` | Voice Chat, custom-llm mode | How long Vapi waits for a reply before giving up (default 120s) |
| `VAPI_SILENCE_TIMEOUT_SECONDS` | Voice Chat, custom-llm mode | How long the whole call can sit silent before Vapi hangs up (default 180s) |
| `VOICE_MAX_TOKENS` / `VOICE_TEMPERATURE` | Voice Chat | Reply length cap and randomness |

## Where to change things

- **Change the local Ollama model** (used for analysis, Text Chat, and custom-llm voice mode): edit `OLLAMA_MODEL` in `backend/.env`, restart the backend. Make sure you've pulled it first: `ollama pull <model-name>`.
- **Change which model Vapi uses for voice**: edit `VAPI_NATIVE_MODEL_PROVIDER` and `VAPI_NATIVE_MODEL` in `backend/.env`, restart the backend. No code changes needed — see [6c](#6c-a-free-model-provider-for-vapi-openrouter).
- **Switch voice back to your local Ollama model** (fully offline, but slow): set `VAPI_LLM_PROVIDER=custom-llm` in `backend/.env`, restart.
- **Change the voice/accent Vapi speaks with**: edit `VAPI_VOICE_ID` (see Vapi's docs for the full voice list for your chosen `VAPI_VOICE_PROVIDER`).
- **Change how long voice replies can be**: `VOICE_MAX_TOKENS` in `backend/.env`.
- **Rewrite how the twin's personality prompt is built**: `backend/app/adapters/ollama_adapter.py` (text) and `vapi_adapter.py` (voice) — these are the only two files that decide prompt *content*; nothing else in the backend touches prompt text.

## Troubleshooting

- **Voice page says "not configured"** — check the exact reason it gives you (it names the missing variable). Usually `PUBLIC_BACKEND_URL` isn't set or `VAPI_PUBLIC_KEY` is empty.
- **Call connects, you hear the greeting, but no reply ever comes** — check the call's detail page in your Vapi dashboard for `endedReason` and the model cost line. A `pipeline-error-*-llm-failed` reason with a 404 almost always means the free model ID you're using got retired — grab a current one from [openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0) and update `VAPI_NATIVE_MODEL`.
- **"Vapi is not a constructor" in the browser console** — a known CJS/ESM bundling quirk with `@vapi-ai/web`; already worked around in `frontend/src/hooks/useVapiCall.js`. If you see it again after a dependency upgrade, that's the file to look at.
- **Text chat replies take a very long time** — this is Ollama running on CPU; a smaller/faster model in `OLLAMA_MODEL` helps. This does not affect Voice Chat, which doesn't use Ollama in the default `vapi-native` mode.
- **ngrok URL changed and voice stopped working** — expected on the free plan every time you restart ngrok. Update `PUBLIC_BACKEND_URL` and restart the backend.
Author -Vaibhav Sutar
