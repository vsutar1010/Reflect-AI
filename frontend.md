# ReflectAI — Frontend Documentation

> **Purpose:** Complete reference for the React/Vite frontend. Feed this file to any AI to get full context of the frontend codebase.
> **Last Updated:** 2026-09-04

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| React | UI framework |
| Vite | Build tool / dev server |
| React Router DOM | Client-side routing (lazy-loaded pages) |
| Framer Motion | Animations & transitions |
| Lucide React | Icon library |
| TailwindCSS | Utility-first CSS |
| PostCSS + Autoprefixer | CSS processing |
| @vapi-ai/web | Vapi Web SDK for voice calls |

See `frontend/package.json` for exact pinned versions.

---

## Full Folder Structure

```
frontend/
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── eslint.config.js
├── package.json
├── public/
└── src/
    ├── main.jsx                    # React DOM root mount
    ├── App.jsx                     # Route definitions + Provider wrapper
    ├── App.css / index.css         # Global styles, Tailwind directives
    ├── assets/                     # Static images (Landing.jsx)
    ├── context/
    │   ├── AuthContext.jsx         # Signed-in user, login/signup/logout/Google methods
    │   └── ProfileContext.jsx      # Selected twin (persisted in localStorage)
    ├── hooks/
    │   └── useVapiCall.js          # Vapi SDK state machine hook for voice calls
    ├── services/
    │   └── api.js                  # Centralized API client (all backend calls)
    ├── pages/
    │   ├── Landing.jsx             # Marketing homepage
    │   ├── Login.jsx               # Email/password + Google Sign-In
    │   ├── Signup.jsx              # Email/password signup + OTP verification step
    │   ├── Analyze.jsx             # 10-question interview flow + WhatsApp import flow
    │   ├── Profiles.jsx            # Profile management grid page
    │   ├── Dashboard.jsx           # Profile detail, stats, Big Five visualization
    │   ├── Chat.jsx                # Full text chat UI, streaming
    │   ├── Voice.jsx               # Full Vapi voice UI
    │   ├── ModeSelect.jsx          # Chat/Voice mode hub (mounted at /mode)
    │   └── Reflect.jsx             # Journaling: compose, history, detail, edit, delete
    └── components/
        ├── common/                 # Reusable UI primitives
        │   ├── Button.jsx
        │   ├── Card.jsx            # Shared glass-card — see Design System note below
        │   ├── Input.jsx
        │   ├── Loader.jsx
        │   ├── Modal.jsx
        │   ├── Navbar.jsx
        │   ├── ProtectedRoute.jsx  # Redirects to /login when not authenticated
        │   ├── GoogleSignInButton.jsx  # Renders only if VITE_GOOGLE_CLIENT_ID is set
        │   └── AnimatedBackground.jsx
        └── features/
            ├── analysis/           # AnalysisSidebar, ProgressCard, QuestionCard
            ├── chat/                # ChatBubble, ChatInput, MessageList, TypingIndicator
            ├── voice/               # CallTimer, ConnectionStatus, SpeakingIndicator,
            │                        # VoiceTranscript, WaveformVisualizer
            ├── profile/             # PersonalityCard, PersonalityChart, ProfileCard,
            │                        # ProfileGrid, StatCard
            └── reflect/              # ReflectEntryCard, ReflectDetailModal, moodStyles.js
```

---

## Entry Points

### src/main.jsx
Mounts React app into `<div id="root">`, wrapped in `StrictMode`.

### src/App.jsx
Every page is lazy-loaded (`React.lazy`) so heavy per-page dependencies (e.g. `@vapi-ai/web`, only needed by Voice) aren't in the first-paint bundle.

```jsx
export default function App() {
  return (
    <AuthProvider>
      <ProfileProvider>
        <Router>
          <Suspense fallback={<Loader fullPage text="Loading..." />}>
            <Routes>
              <Route path="/"          element={<Landing />} />
              <Route path="/login"     element={<Login />} />
              <Route path="/signup"    element={<Signup />} />
              <Route path="/analyze"   element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/reflect"   element={<ProtectedRoute><Reflect /></ProtectedRoute>} />
              <Route path="/mode"      element={<ProtectedRoute><ModeSelect /></ProtectedRoute>} />
              <Route path="/chat"      element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/voice"     element={<ProtectedRoute><Voice /></ProtectedRoute>} />
              <Route path="/profiles"  element={<ProtectedRoute><Profiles /></ProtectedRoute>} />
            </Routes>
          </Suspense>
        </Router>
      </ProfileProvider>
    </AuthProvider>
  );
}
```

---

## Route Map

| Route | Component | Auth | Description |
|-------|-----------|------|-------------|
| `/` | Landing.jsx | Public | Marketing homepage |
| `/login` | Login.jsx | Public | Email/password + Google Sign-In |
| `/signup` | Signup.jsx | Public | Email/password signup + OTP step |
| `/analyze` | Analyze.jsx | Protected | Interview or WhatsApp import → creates a profile |
| `/profiles` | Profiles.jsx | Protected | Profile list/select/delete |
| `/dashboard` | Dashboard.jsx | Protected | Profile detail, stats, Big Five chart |
| `/reflect` | Reflect.jsx | Protected | Journaling — compose, history, detail, edit, delete |
| `/mode` | ModeSelect.jsx | Protected | Chat vs. Voice mode hub |
| `/chat` | Chat.jsx | Protected | Full text chat UI, streaming |
| `/voice` | Voice.jsx | Protected | Full Vapi voice call UI |

**`ProtectedRoute`** renders a full-page loader while the initial `api.me()` check is in flight, then redirects to `/login` if there's no authenticated user.

---

## Context

### src/context/AuthContext.jsx
`useAuth()` provides: `user`, `authLoading`, `requestSignupOtp(email, password, name)`, `verifySignupOtp(email, otp)`, `login(email, password)`, `loginWithGoogle(credential)`, `logout()`. On mount, calls `api.me()` once to restore the session from the cookie; failure just means `user = null` (not an error state).

### src/context/ProfileContext.jsx
`useProfile()` provides: `profiles`, `selectedProfile`, `selectProfile(profile)`, `removeProfile(id)`, `fetchProfiles()`, `loadingProfiles`, `error`. **localStorage key:** `reflect_active_profile`.

---

## Hooks

### src/hooks/useVapiCall.js
Wraps the Vapi Web SDK into a React state machine. Returns `status` (`idle`→`connecting`→`connected`→`ended`/`error`), `error`, `isAssistantSpeaking`, `isListening`, `volumeLevel`, `micLevel`, `transcript`, `callDuration`, `connect()`, `disconnect()`. `connect()` calls `api.startVoiceSession(profileId)`, seeds the transcript with `assistant.firstMessage`, then opens the Vapi call. Registers all Vapi event listeners (`call-start`, `call-end`, `speech-start/end`, `volume-level`, `local-volume-level`, `message`, `call-start-failed`, `error`). `toErrorMessage()` normalizes every Vapi error shape into a plain string safe for JSX.

---

## Services

### src/services/api.js

**Base URL:** `http://localhost:8000/api`. Every request sends `credentials: 'include'` (the session cookie). `handleResponse()` throws `Error(detail)` from the backend's error body, and appends a "try again in about N minutes" hint when the response is `429` with a `Retry-After` header.

```js
export const api = {
  // Auth
  requestSignupOtp({ email, password, name }),
  verifySignupOtp({ email, otp }),
  login({ email, password }),
  loginWithGoogle(credential),
  logout(),
  me(),

  // Profiles
  getProfiles(), getProfile(id), deleteProfile(id),
  getProfileConversations(id), setProfileVoice(id, gender),

  // Analysis Flow
  startAnalysis(), sendAnalysisMessage(sessionId, message),
  finalizeAnalysis(sessionId, profileName),

  // WhatsApp Chat Import
  uploadWhatsAppChat(file),               // multipart/form-data
  finalizeWhatsAppChat(uploadId, targetSender, profileName),

  // Chat Flow
  startChat(profileId),
  sendChatMessage(sessionId, message),        // non-streaming JSON
  streamChatMessage(sessionId, message, { onDelta, onDone, onError, signal }),  // SSE

  // Reflect / Journaling
  createReflectEntry(profileId, content),
  getReflectEntries(profileId, { limit, skip }),
  getReflectEntry(id), updateReflectEntry(id, content),
  reanalyzeReflectEntry(id), deleteReflectEntry(id),

  // Voice Chat Flow (Vapi)
  getVoiceConfig(), startVoiceSession(profileId), endVoiceSession(sessionId),
};
```

`streamSSE()` (internal helper) reads a `text/event-stream` response as `data: {...}\n\n` frames, dispatching `onDelta({delta})`, `onDone()`, or `onError(message)` — this is what `streamChatMessage` and `Chat.jsx` build on for progressive token rendering.

---

## Pages (Detailed)

### src/pages/Landing.jsx
Hero (CTA to `/signup`), Features, How It Works, Technology, Pricing, Footer. Includes a simulated demo chat widget with hardcoded keyword responses (`setTimeout`) — cosmetic only, not connected to the real API.

### src/pages/Login.jsx / Signup.jsx
Email/password forms plus `GoogleSignInButton.jsx` (renders only if `VITE_GOOGLE_CLIENT_ID` is set). `Signup.jsx` has two stages: request OTP → enter the 6-digit code → account created + session cookie set. Error display is generic (`err.message` from the thrown `Error`) — the backend intentionally returns identical error text for different failure causes on the login/signup-OTP endpoints (account-enumeration protection), so the frontend never special-cases specific error strings.

### src/pages/Analyze.jsx
Two paths to a profile: the 10-question interview flow (`ProgressCard` + `QuestionCard` + `AnalysisSidebar`), or a WhatsApp chat export upload (client-side size check against `MAX_WHATSAPP_UPLOAD_MB`, then upload → pick the target sender from detected participants → finalize). Both end by navigating to `/dashboard` with the new profile selected.

### src/pages/Profiles.jsx
3 render states: loading spinner → empty-state CTA → Active Twin Banner + `ProfileGrid`. Delete goes through a confirm modal.

### src/pages/Dashboard.jsx
Profile header, `StatCard` row (conversations, words analyzed, last used), `PersonalityCard` (personality dimensions, topics, values, summary) alongside `PersonalityChart` (Big Five bar chart + radar chart — see [PersonalityChart.jsx](#personalitychartjsx) below), conversation history list, quick actions (Start Chat, Voice Chat).

### src/pages/Chat.jsx
**State:** `sessionId`, `messages`, `loading`, `sending`/streaming state, `error`. On mount, calls `api.startChat(selectedProfile.id)`. `handleSend(text)` adds the user message optimistically, then calls `api.streamChatMessage(...)`, appending each `onDelta` chunk to a placeholder assistant message so it grows progressively on screen; `onDone` finalizes it, `onError` surfaces the error. Uses an `AbortController` so navigating away mid-stream cancels the fetch cleanly. Falls back to the non-streaming path automatically if the browser doesn't support the streaming read loop.

### src/pages/Voice.jsx
`api.getVoiceConfig()` on render decides whether to show setup instructions (with the backend's stated reason) or the call UI. Layout: header (profile name + `CallTimer` + `ConnectionStatus`), error banner, main card (`SpeakingIndicator`, "Speaking.../Listening..." label, `WaveformVisualizer`, Connect/Disconnect button, `VoiceTranscript`).

### src/pages/ModeSelect.jsx
Two cards: "Text Chat" → `/chat`, "Voice Chat" → `/voice`. Mounted at `/mode`.

### src/pages/Reflect.jsx
**State:** `content` (compose textarea, capped at `MAX_CONTENT_LENGTH = 8000`), `stage` (`idle`|`saving`|`analyzing`), `entries` (paginated, `PAGE_SIZE = 20`), `selectedEntry` (opens `ReflectDetailModal`). Save-and-Reflect calls `api.createReflectEntry`, which returns the entry with its analysis already attempted; the new entry is prepended to the list. Clicking an entry opens `ReflectDetailModal` (original text + AI reflection: mood badge, themes, reflection, observations, next step); Edit re-saves via `api.updateReflectEntry` (clears + re-runs analysis server-side); a failed analysis shows a "try analysis again" action wired to `api.reanalyzeReflectEntry`. Delete goes through a confirm modal via `ReflectEntryCard`.

---

## Common Components (Detailed)

### Card.jsx
**Props:** `children`, `className`, `hover` (lift -4px), `glow` (blue border on hover), `onClick`.
**Base style:** `bg-[#09090B]/60 border border-white/10 rounded-2xl p-6`.

> **Design note:** `Card.jsx` previously also carried `backdrop-blur-xl`. It was removed as a performance fix — `Card` is the shared primitive behind every repeated card in the app (`ProfileCard`, `StatCard`, `PersonalityCard`, `ReflectEntryCard`, `QuestionCard`), and stacking many simultaneous `backdrop-filter` surfaces in a grid/list is expensive to composite. The semi-transparent background alone reproduces the same visual look against this app's near-flat page background, without the cost. Blur is still used, deliberately, on a handful of single/limited elements: `Navbar.jsx`, `Modal.jsx`, `Loader.jsx`, the main `Chat.jsx`/`Voice.jsx` panels, `ChatInput.jsx`, and the Landing page's hero/nav elements. `ChatBubble.jsx` and `TypingIndicator.jsx` similarly dropped their own blur, since they render inside `Chat.jsx`'s already-blurred outer panel (nested blur was nearly invisible but doubled the compositing cost per message).

### Modal.jsx
**Props:** `isOpen`, `onClose`, `title`, `children`, `maxWidth`. Body scroll lock, Escape key → close, backdrop click → close, backdrop keeps `backdrop-blur-md` (a limited, single-instance overlay). Framer Motion `AnimatePresence`.

### Navbar.jsx
Fixed floating pill, keeps `backdrop-blur-xl` (single persistent overlay). Desktop: logo, anchor links, Profiles + auth links. Mobile: hamburger menu. Anchor hash links (`#features`, etc.) only scroll correctly on the Landing page — they appear on every page since Navbar is shared everywhere.

### Loader.jsx
**Props:** `text`, `fullPage`. Full-page mode keeps a `backdrop-blur-md` overlay.

### Other common components
`Button.jsx` (variants: primary/secondary/danger/ghost; sizes sm/md/lg; loading + icon support), `Input.jsx` (label, icon, error state), `ProtectedRoute.jsx` (see [Route Map](#route-map) above), `AnimatedBackground.jsx` (low-opacity dot-grid background layer, shared across pages).

---

## Feature Components (Detailed)

### PersonalityChart.jsx
Renders the Big Five (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) as horizontal bars plus an inline-SVG radar chart (no charting library — five axes is simple enough for plain trig + a `<polygon>`). `normalizeScore()` accepts a 0–1 fraction, an already-0–100 number, a numeric string (optionally with `%`), or an object carrying the score under `score`/`value`/`percentage`/`percent` — returns `null` (rendered as "N/A") for anything unparseable, never throws. Trait key lookup tolerates common LLM key variants (`openness_to_experience`, `extroversion`, etc.) via an alias list, case-insensitively. When *no* trait has a score at all, shows "Personality insights aren't available yet" instead of an empty chart — this is the state an existing profile is in until it's re-analyzed under the current Big Five schema.

### ProfileGrid.jsx / ProfileCard.jsx / StatCard.jsx / PersonalityCard.jsx
Unchanged in shape from before — `ProfileGrid` is a responsive grid ("Create New Twin" tile + `ProfileCard` per profile), `ProfileCard` has an avatar/stats/active-state/delete-modal, `StatCard` is an icon+label+value block, `PersonalityCard` shows tone/style/topics/summary text fields (distinct from the numeric `PersonalityChart`).

### Chat feature components
`ChatBubble.jsx` (user right/blue-gradient, assistant left/dark-panel, no longer independently blurred — see the Card.jsx note above), `ChatInput.jsx` (auto-growing textarea, Enter to send, disabled while sending), `MessageList.jsx` (auto-scrolls to bottom, renders streaming deltas as they arrive), `TypingIndicator.jsx` (three-dot animation, same bubble style as an assistant message, blur removed for the same nested-blur reason as `ChatBubble`).

### Reflect feature components
`ReflectEntryCard.jsx` — history list item: date, mood badge (or a pending/failed status badge), truncated content preview, delete button. `ReflectDetailModal.jsx` — full original entry + full AI reflection (mood, themes, reflection, observations, next step), Edit (inline textarea, Save re-runs analysis) and Delete actions. `moodStyles.js` — maps each mood string to a badge color class.

### Voice feature components
`CallTimer.jsx`, `ConnectionStatus.jsx`, `SpeakingIndicator.jsx`, `VoiceTranscript.jsx`, `WaveformVisualizer.jsx` — unchanged in shape; see prop tables in git history if needed, or read the files directly (each is short and self-contained).

---

## Design System

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| Page Background | `#050505` | All page backgrounds |
| Card Background | `#09090B` at 60–70% opacity | All card surfaces (no blur on repeated cards — see Card.jsx note above) |
| Primary Blue | `#4F8BFF` | Primary accents, active borders, glows |
| Primary Purple | `#8B5CF6` | Secondary accents, gradient end |
| Text Primary | `#F8FAFC` | Headings and important text |
| Text Muted | `slate-400` | Descriptions, labels, subtext |
| Border Default | `white/10` | All card borders |
| Danger | `red-500` at 10–30% | Delete buttons, error states |
| Success | `emerald-500` at 10–30% | Completion states |

### Primary Gradient
```
from-[#4F8BFF] to-[#8B5CF6]
```
Used on primary buttons, progress bars, hero heading, avatar circles, logo dot, glow backgrounds.

### Standard Page Layout
```jsx
<div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] font-sans pb-24">
  <AnimatedBackground />
  <Navbar />
  <main className="relative z-10 max-w-7xl mx-auto px-6 pt-36">
    {/* Page content */}
  </main>
</div>
```

---

## Reusable Patterns

### No Profile Guard (Chat, Voice, Dashboard, Reflect)
When `selectedProfile` is null, these pages show a "No Twin Selected" fallback with a CTA to `/profiles`, rather than erroring.

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
```

### Error Banner
```jsx
{error && (
  <div className="mb-8 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3 text-red-400 text-sm">
    <AlertCircle className="w-5 h-5 shrink-0" />
    <span>{error}</span>
  </div>
)}
```

---

## How to Run Frontend

```bash
cd frontend
npm install
npm run dev     # Dev server at http://localhost:5173
npm run build   # Production build to ./dist
npm run preview # Preview production build
npm run lint    # ESLint
```

**Prerequisites:** Backend running at `http://localhost:8000` (which itself needs MongoDB + Ollama — see `backend.md`). For Google Sign-In: `VITE_GOOGLE_CLIENT_ID` in frontend `.env`, matching the backend's `GOOGLE_CLIENT_ID`. For Voice Chat: backend's Vapi config + tunnel set up (see `README.md`).
