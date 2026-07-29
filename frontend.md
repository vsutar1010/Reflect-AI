# ReflectAI — Frontend Documentation

> **Purpose:** Complete reference for the React/Vite frontend. Feed this file to any AI to get full context of the frontend codebase — every file, folder, component, state, prop, hook, and API call is documented here.
> **Last Updated:** 2026-07-29

---

## Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| React | ^19.2.7 | UI framework |
| Vite | ^8.1.1 | Build tool / dev server |
| React Router DOM | ^7.11.0 | Client-side routing |
| Framer Motion | ^12.42.2 | Animations & transitions |
| Lucide React | ^1.25.0 | Icon library |
| TailwindCSS | ^3.4.19 | Utility-first CSS |
| PostCSS + Autoprefixer | ^8.5.19 / ^10.5.4 | CSS processing |
| @vapi-ai/web | latest | Vapi Web SDK for voice calls |

---

## Full Folder Structure

```
frontend/
├── index.html                      # Vite HTML entry point. Mounts <div id="root">
├── vite.config.js                  # Vite config — uses @vitejs/plugin-react
├── tailwind.config.js              # Tailwind config (minimal, content paths set)
├── postcss.config.js               # PostCSS config for Tailwind + Autoprefixer
├── eslint.config.js                # ESLint flat config (react-hooks, react-refresh plugins)
├── package.json                    # Dependencies (see Tech Stack above)
├── .gitignore                      # Ignores node_modules, dist, .env
├── public/                         # Static assets served at root URL
└── src/
    ├── main.jsx                    # React DOM root mount
    ├── App.jsx                     # Route definitions + Provider wrapper
    ├── App.css                     # Global gradient/glow animation keyframes
    ├── index.css                   # Tailwind directives (@base, @components, @utilities)
    ├── assets/                     # Static images imported in Landing.jsx
    │   ├── hero.png
    │   ├── voice1.jpg, voice2.jpg
    │   ├── img1.jpg, img2.jpg, img3.jpg
    │   ├── chat1.jpg, chat2.jpg
    ├── context/
    │   └── ProfileContext.jsx      # Global profile state (React Context + localStorage)
    ├── hooks/
    │   └── useVapiCall.js          # NEW: Vapi SDK state machine hook for voice calls
    ├── services/
    │   └── api.js                  # Centralized API client (12 methods)
    ├── pages/
    │   ├── Landing.jsx             # DONE: Marketing homepage (~519 lines)
    │   ├── Analyze.jsx             # DONE: 10-question personality interview flow
    │   ├── Profiles.jsx            # DONE: Profile management grid page
    │   ├── Dashboard.jsx           # DONE: Profile detail, personality, stats (~580 lines)
    │   ├── Chat.jsx                # DONE: Full text chat UI (~260 lines)
    │   ├── Voice.jsx               # DONE: Full Vapi voice UI (~181 lines)
    │   ├── ModeSelect.jsx          # DONE: Chat/Voice mode hub (~178 lines)
    │   └── Reflect.jsx             # STUB: feature not yet designed
    └── components/
        ├── common/                 # Reusable UI primitives
        │   ├── Button.jsx          # DONE: Multi-variant animated button
        │   ├── Card.jsx            # DONE: Glassmorphism card container
        │   ├── Input.jsx           # DONE: Styled input with icon + error support
        │   ├── Loader.jsx          # DONE: Animated spinner (inline or full-page)
        │   ├── Modal.jsx           # DONE: Animated overlay modal dialog
        │   └── Navbar.jsx          # DONE: Fixed floating navbar with mobile menu
        └── features/
            ├── analysis/           # Components used in /analyze
            │   ├── AnalysisSidebar.jsx   # DONE: Step checklist sidebar
            │   ├── ProgressCard.jsx      # DONE: Animated progress bar
            │   └── QuestionCard.jsx      # DONE: Question display + answer textarea
            ├── chat/               # All DONE (previously empty stubs)
            │   ├── ChatBubble.jsx        # DONE: Message bubble (user right / assistant left)
            │   ├── ChatInput.jsx         # DONE: Textarea + send button
            │   ├── MessageList.jsx       # DONE: Scrollable container, auto-scroll
            │   └── TypingIndicator.jsx   # DONE: Animated 3-dot loading indicator
            ├── voice/              # NEW: All DONE
            │   ├── CallTimer.jsx         # DONE: MM:SS call duration display
            │   ├── ConnectionStatus.jsx  # DONE: Status badge (idle/connecting/connected/ended/error)
            │   ├── SpeakingIndicator.jsx # DONE: Avatar with pulsing ring when speaking
            │   ├── VoiceTranscript.jsx   # DONE: Live scrolling transcript
            │   └── WaveformVisualizer.jsx# DONE: Animated audio waveform bars
            └── profile/
                ├── PersonalityCard.jsx   # DONE: Personality dimensions display
                ├── ProfileCard.jsx       # DONE: Single profile card with delete modal
                ├── ProfileGrid.jsx       # DONE: Grid of ProfileCards + "Create New" tile
                └── StatCard.jsx          # DONE: Stat display (icon + label + value)
```

---

## Entry Points

### src/main.jsx
Mounts React app into `<div id="root">` in index.html. Wraps in StrictMode.

### src/App.jsx
All routes defined here. ProfileProvider wraps everything.

```jsx
export default function App() {
  return (
    <ProfileProvider>
      <Router>
        <Routes>
          <Route path="/"          element={<Landing />} />
          <Route path="/analyze"   element={<Analyze />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profiles"  element={<Profiles />} />
          <Route path="/reflect"   element={<ModeSelect />} />  {/* mode hub */}
          <Route path="/chat"      element={<Chat />} />
          <Route path="/voice"     element={<Voice />} />
        </Routes>
      </Router>
    </ProfileProvider>
  );
}
```

---

## Route Map

| Route | Component | Status | Description |
|-------|-----------|--------|-------------|
| `/` | Landing.jsx | DONE | Marketing homepage |
| `/analyze` | Analyze.jsx | DONE | Personality interview |
| `/profiles` | Profiles.jsx | DONE | Profile list/select/delete |
| `/dashboard` | Dashboard.jsx | DONE | Profile detail, stats, personality |
| `/reflect` | ModeSelect.jsx | DONE | Chat vs. Voice mode hub |
| `/chat` | Chat.jsx | DONE | Full text chat UI |
| `/voice` | Voice.jsx | DONE | Full Vapi voice call UI |

---

## Context

### src/context/ProfileContext.jsx

**Purpose:** Global state for personality profiles. Any page can access active profile and list without prop drilling.

**Provides via `useProfile()` hook:**

| Value | Type | Description |
|-------|------|-------------|
| `profiles` | Array | All profile summaries from backend |
| `selectedProfile` | Object or null | Active profile (also persisted in localStorage) |
| `selectProfile(profile)` | Function | Sets active profile + writes to localStorage |
| `removeProfile(id)` | async Function | DELETE /api/profiles/:id, clears selection if deleted |
| `fetchProfiles()` | async Function | Refreshes list from backend |
| `loadingProfiles` | Boolean | True while fetching |
| `error` | String or null | Error message if fetch fails |

**localStorage key:** `reflect_active_profile`

---

## Hooks

### src/hooks/useVapiCall.js — NEW

**Purpose:** Wraps the Vapi Web SDK into a React state machine. Used by Voice.jsx.

**Parameters:** `profileId` (string)

**Returns:**
| Value | Type | Description |
|-------|------|-------------|
| `status` | string | `idle` → `connecting` → `connected` → `ended` / `error` |
| `error` | string or null | Normalized error message |
| `isAssistantSpeaking` | boolean | True during Vapi speech-start events |
| `isListening` | boolean | True when connected and assistant not speaking |
| `volumeLevel` | number | 0–1 volume level from Vapi (for waveform) |
| `micLevel` | number | 0–1 local microphone level |
| `transcript` | Array | `[{ role, text, final }]` — live conversation transcript |
| `callDuration` | number | Seconds since call connected |
| `connect()` | async Function | Starts session: calls backend, then `vapi.start(assistant_config)` |
| `disconnect()` | Function | Calls `vapi.stop()`, ends backend session |

**connect() flow:**
1. `api.startVoiceSession(profileId)` → gets `{ session_id, public_key, assistant }`
2. Seeds transcript with `assistant.firstMessage` immediately
3. `new Vapi(public_key)` + registers all event listeners
4. `vapi.start(assistant)` — Vapi opens WebRTC call

**Event listeners registered:**
- `call-start` → setStatus('connected'), start timer
- `call-end` → setStatus('ended'), endBackendSession
- `speech-start` → setIsAssistantSpeaking(true)
- `speech-end` → setIsAssistantSpeaking(false)
- `volume-level` → setVolumeLevel
- `local-volume-level` → setMicLevel
- `message` (type=transcript) → updates transcript array (partial/final)
- `call-start-failed` → setStatus('error')
- `error` → setStatus('error')

**Error normalization:** `toErrorMessage()` handles all Vapi error shapes (string, Error, nested objects) → always returns a plain string safe for JSX rendering.

---

## Services

### src/services/api.js

**Base URL:** `http://localhost:8000/api`

**All exported API methods:**
```js
export const api = {
  // Profiles
  getProfiles()                         // GET    /profiles
  getProfile(id)                        // GET    /profiles/:id
  deleteProfile(id)                     // DELETE /profiles/:id
  getProfileConversations(id)           // GET    /profiles/:id/conversations

  // Analysis Flow (must be called in order)
  startAnalysis()                       // POST   /analyze/start
  sendAnalysisMessage(sessionId, msg)   // POST   /analyze/message
  finalizeAnalysis(sessionId, name)     // POST   /analyze/finalize

  // Chat Flow
  startChat(profileId)                  // POST   /chat/start
  sendChatMessage(sessionId, msg)       // POST   /chat/message

  // Voice Chat Flow (Vapi) — NEW
  getVoiceConfig()                      // GET    /voice/config
  startVoiceSession(profileId)          // POST   /voice/start
  endVoiceSession(sessionId)            // POST   /voice/end
}
```

FastAPI error detail field is extracted and re-thrown as `Error(detail)`.

---

## Pages (Detailed)

### src/pages/Landing.jsx — DONE (~95%)

**Sections:** Hero (CTA to /analyze, simulated demo chat), Features, How It Works, Technology, Pricing, Footer.

**Demo chat:** Simulated, no real API. Hardcoded keyword responses. `setTimeout(1800ms)`.

**Image imports from `../assets/`:** hero.png, voice1.jpg, voice2.jpg, img1.jpg, img2.jpg, img3.jpg, chat1.jpg, chat2.jpg

---

### src/pages/Analyze.jsx — DONE (~90%)

**Purpose:** 10-question personality analysis interview → finalize → navigate to /dashboard.

**State:**
| State | Purpose |
|-------|---------|
| `sessionId` | Active backend session UUID |
| `question` | Current question text |
| `progress` | 0-100 progress % |
| `currentQuestionIndex` | Which question (0-indexed) |
| `isCompleted` | True after all questions answered |
| `loading` | True while starting session |
| `submitting` | True while submitting answer |
| `finalizing` | True while generating/saving profile |
| `profileName` | Name user gives their digital twin |
| `error` | Error message string or null |

**3 render states:** loading spinner → interview grid (ProgressCard + QuestionCard + AnalysisSidebar) → completion card (name input + finalize button)

---

### src/pages/Profiles.jsx — DONE (~85%)

**Purpose:** Lists all profiles, allows selecting active twin, creating new, or deleting.

**3 render states:** loading spinner → empty state CTA → Active Twin Banner + ProfileGrid

**Active Twin Banner:** Avatar, "Currently Active Twin" label, "View Dashboard" → /dashboard, "Start Chat" → /chat buttons.

---

### src/pages/Dashboard.jsx — DONE (~80%)

**Purpose:** Shows the selected profile's personality data, stats, and conversation history.

**State:**
| State | Purpose |
|-------|---------|
| `profileData` | Full profile data from GET /api/profiles/:id |
| `conversations` | List from GET /api/profiles/:id/conversations |
| `loading` | Loading indicator |
| `error` | Error message |

**Sections:**
- Profile header: avatar, name, creation date
- Stats row using StatCard: conversation count, created date, last used
- PersonalityCard: personality dimensions, topics, values, summary
- Conversation history list (from /api/profiles/:id/conversations)
- Quick action buttons: Start Chat → /chat, Voice Chat → /voice

**Missing:** Personality radar/bar charts (Big 5 visualization), profile rename functionality.

---

### src/pages/Chat.jsx — DONE (~85%)

**Purpose:** Full text chat UI with the digital twin.

**State:**
| State | Purpose |
|-------|---------|
| `sessionId` | Active backend chat session |
| `messages` | Array of `{ role, content }` displayed in MessageList |
| `loading` | True while starting session |
| `sending` | True while waiting for reply |
| `error` | Error message |

**Flow:**
```
Mount → startChatSession():
  api.startChat(selectedProfile.id) → { session_id, message }
  → setSessionId, add opening message to messages

User types → handleSend(text):
  Add user message to messages immediately (optimistic)
  setIsTyping(true)
  api.sendChatMessage(sessionId, text) → { reply }
  Add assistant reply to messages
  setIsTyping(false)
```

**Components used:** MessageList → ChatBubble, TypingIndicator, ChatInput

**Known gap:** Non-streaming — full reply appears at once after Ollama completes generation.

---

### src/pages/Voice.jsx — DONE (~85%)

**Purpose:** Full Vapi voice call interface.

**Setup flow on render:**
1. `api.getVoiceConfig()` — checks if Vapi is configured
2. If not enabled: shows setup instructions with reason from backend
3. If enabled: shows call UI with Connect button

**State from `useVapiCall(selectedProfile?.id)` hook:**
`status`, `error`, `isAssistantSpeaking`, `isListening`, `volumeLevel`, `transcript`, `callDuration`, `connect`, `disconnect`

**Layout:**
- Header: profile name + CallTimer + ConnectionStatus
- Error banner (if error)
- Main card:
  - SpeakingIndicator (avatar with pulsing ring)
  - "Speaking..." / "Listening..." label
  - WaveformVisualizer (blue when speaking, purple when listening)
  - Connect / Disconnect button
  - VoiceTranscript (live scrolling conversation)
- Footer note: "Voice replies run through the same personality engine as Text Chat."

**Known gap:** High latency (3–7s per reply) when `VAPI_LLM_PROVIDER=custom-llm` due to local Ollama CPU TTFT.

---

### src/pages/ModeSelect.jsx — DONE (~80%)

**Purpose:** Mode selection hub between Chat and Voice. Mounted at `/reflect` route.

Shows two large cards: "Text Chat" → /chat and "Voice Chat" → /voice. Displays selected profile name.

---

### src/pages/Reflect.jsx — STUB (~10%)

Current code is minimal placeholder. Reflection/journaling feature not yet designed.

---

## Common Components (Detailed)

### Button.jsx

**Props:** `children`, `variant` ('primary'|'secondary'|'danger'|'ghost'), `size` ('sm'|'md'|'lg'), `loading`, `disabled`, `onClick`, `type`, `className`, `icon` (LucideIcon)

**Variants:**
- primary: Blue→Purple gradient, glow shadow
- secondary: Dark glass bg, white border
- danger: Red tinted bg/border, red glow
- ghost: Transparent, hover white/5 bg

**Animation:** Framer Motion `whileHover scale(1.02)`, `whileTap scale(0.98)`. Disabled when `loading` or `disabled`.

---

### Card.jsx

**Props:** `children`, `className`, `hover` (lift -4px), `glow` (blue border on hover), `onClick`

**Base style:** `bg-[#09090B]/60 backdrop-blur-xl border border-white/10 rounded-2xl p-6`

---

### Input.jsx

**Props:** `label`, `error`, `icon` (LucideIcon), `id`, plus all native input props

**Styling:** Dark glass. Focus border: `#4F8BFF`. Error border: red.

---

### Loader.jsx

**Props:** `text` (default 'Loading...'), `fullPage` (boolean)

**Visual:** Pulsing glow ring + spinning Loader2 icon in blue.

---

### Modal.jsx

**Props:** `isOpen`, `onClose`, `title`, `children`, `maxWidth` (default 'max-w-md')

**Side effects:** Body scroll lock, Escape key → onClose, backdrop click → onClose.

**Animation:** Framer Motion AnimatePresence. opacity 0→1, scale 0.95→1, y 10→0.

---

### Navbar.jsx

**Structure:** Fixed floating pill at top. Desktop: logo left, anchor links center, Profiles + Get Started right. Mobile: hamburger toggle.

**Note:** Anchor hash links (Features, How it Works, etc.) only scroll on Landing page (/). They appear on all pages since Navbar is shared.

---

## Feature Components (Detailed)

### ProgressCard.jsx
**Props:** `progress` (0-100), `currentQuestion` (1-indexed), `totalQuestions`

Animated gradient progress bar using `motion.div` width transition. Blue→Purple gradient fill.

### QuestionCard.jsx
**Props:** `question` (string), `onSubmit` (function), `loading` (bool), `questionIndex` (number)

Local state: `answer` (string) — resets to '' when `questionIndex` changes. Ctrl+Enter submits. Character count bottom-right.

### AnalysisSidebar.jsx
**Props:** `currentStep` (0-indexed), `totalSteps` (default 10), `answersCount`

Vertical checklist: done (green check), current (blue highlight), pending (grey). Privacy tip card below.

### ProfileGrid.jsx
**Props:** `profiles`, `selectedProfile`, `onSelect`, `onDelete`

3-column responsive grid. First tile: "Create New Digital Twin" → /analyze. Remaining tiles: ProfileCard.

### ProfileCard.jsx
**Props:** `profile` ({id, name, created_at, last_used, conversation_count}), `isActive`, `onSelect`, `onDelete`

Local state: `showDeleteModal`, `deleting`. Trash icon → confirm modal → DELETE API call.

### PersonalityCard.jsx
**Props:** `profileData` (full profile object or null)

Reads: tone, communication_style, humor, directness, energy, sentence_length, confidence, preferred_topics, values, summary. Supports both wrapped (`profileData.profile`) and flat formats.

### StatCard.jsx
**Props:** `icon` (LucideIcon), `label`, `value`, `subtext` (optional), `color` ('blue'|'purple'|'green')

Colored icon badge left + text block right.

---

## Voice Components (NEW)

### CallTimer.jsx
**Props:** `seconds` (number), `active` (boolean)

Displays `MM:SS` formatted duration. Only animates when `active` is true.

### ConnectionStatus.jsx
**Props:** `status` ('idle'|'connecting'|'connected'|'ended'|'error')

Colored status badge with matching icon. Green pulse animation when connected.

### SpeakingIndicator.jsx
**Props:** `twinName`, `isAssistantSpeaking`, `isListening`, `connected`

Large avatar circle (first letter of twin name) with:
- Pulsing blue ring animation when `isAssistantSpeaking`
- Steady purple ring when `isListening`
- Dim when disconnected

### VoiceTranscript.jsx
**Props:** `transcript` (Array of `{role, text, final}`), `twinInitial` (string)

Scrollable list of transcript entries. User entries right-aligned, assistant left-aligned (with avatar circle). Partial transcripts shown in lighter color, final in full white.

### WaveformVisualizer.jsx
**Props:** `level` (0–1), `active` (bool), `color` ('blue'|'purple')

Row of animated bars. Bar heights driven by `level` + randomized per-bar offsets. Flat (minimal height) when not active.

---

## Chat Components (Previously Stubs — Now DONE)

### ChatBubble.jsx
User messages: right-aligned, blue gradient bg. Assistant messages: left-aligned, dark glass bg with avatar circle. Framer Motion entrance animation.

### ChatInput.jsx
Auto-growing textarea. Send button disabled when empty or sending. Enter to send, Shift+Enter for newline. Disabled while `sending` prop is true.

### MessageList.jsx
Scrollable `overflow-y-auto` container. Auto-scrolls to bottom when new messages arrive (useEffect + ref). Maps messages array to ChatBubble. Filters system messages from display.

### TypingIndicator.jsx
Three bouncing dots animation. Same left-aligned bubble style as assistant messages. Shown while `isTyping` prop is true.

---

## Design System

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| Page Background | `#050505` | All page backgrounds |
| Card Background | `#09090B` at 60% opacity | All card surfaces |
| Primary Blue | `#4F8BFF` | Primary accents, active borders, glows |
| Primary Purple | `#8B5CF6` | Secondary accents, gradient end |
| Text Primary | `#F8FAFC` | Headings and important text |
| Text Muted | `slate-400` (#94a3b8) | Descriptions, labels, subtext |
| Border Default | `white/10` | All card borders |
| Border Active | `white/20` | Hover borders |
| Danger | `red-500` at 10-30% | Delete buttons, error states |
| Success | `emerald-500` at 10-30% | Completion states |

### Primary Gradient
```
from-[#4F8BFF] to-[#8B5CF6]
```
Used on: primary buttons, progress bars, hero heading, avatar circles, logo dot, glow backgrounds.

### Background Glow Pattern (all pages)
```jsx
<div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[#4F8BFF]/10 blur-[150px]" />
<div className="absolute top-[20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[#8B5CF6]/10 blur-[150px]" />
```

### Standard Page Layout
```jsx
<div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] font-sans pb-24">
  {/* Background Glows */}
  <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
    <div className="absolute top-[-10%] left-[-10%] ... bg-[#4F8BFF]/10 blur-[150px]" />
    <div className="absolute top-[20%] right-[-10%] ... bg-[#8B5CF6]/10 blur-[150px]" />
  </div>
  <Navbar />
  <main className="relative z-10 max-w-7xl mx-auto px-6 pt-36">
    {/* Page content */}
  </main>
</div>
```

---

## Reusable Patterns

### Error Banner
```jsx
{error && (
  <div className="mb-8 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3 text-red-400 text-sm">
    <AlertCircle className="w-5 h-5 shrink-0" />
    <span>{error}</span>
  </div>
)}
```

### Async Loading Pattern
```jsx
const [loading, setLoading] = useState(false);
const doSomething = async () => {
  setLoading(true);
  try {
    await api.someCall();
  } catch (err) {
    setError(err.message || 'Fallback error');
  } finally {
    setLoading(false);
  }
};
// Button receives loading={loading} → auto-shows spinner
```

### No Profile Guard (used in Chat, Voice, Dashboard)
```jsx
if (!selectedProfile) {
  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <Navbar />
      <div className="pt-40 flex flex-col items-center text-center px-6">
        {/* Icon + heading + CTA to /profiles */}
      </div>
    </div>
  );
}
```

---

## How to Run Frontend

```bash
cd frontend
npm install
npm run dev     # Dev server at http://localhost:5173
npm run build   # Production build to ./dist
npm run preview # Preview production build
```

**Prerequisites:**
- Backend must be running at `http://localhost:8000`
- Ollama must be running locally with model pulled
- For Voice Chat: `VAPI_PUBLIC_KEY` in backend `.env` + ngrok tunnel running

**Environment variable:** `VITE_VAPI_PUBLIC_KEY` can be set in frontend `.env` as an alternative to reading from the backend config endpoint (the backend `/api/voice/config` endpoint is the primary source).
