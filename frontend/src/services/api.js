const API_BASE = 'http://localhost:8000/api';

async function handleResponse(res) {
  if (!res.ok) {
    let errorMsg = `API Error: ${res.status} ${res.statusText}`;
    try {
      const errorData = await res.json();
      if (errorData.detail) errorMsg = errorData.detail;
    } catch (_) {}

    // Surface how long to wait, when the server tells us (e.g. login
    // rate limiting) — appended to whatever message the backend sent,
    // not a replacement for it.
    if (res.status === 429) {
      const retryAfter = parseInt(res.headers.get('retry-after'), 10);
      if (Number.isFinite(retryAfter) && retryAfter > 0) {
        const minutes = Math.ceil(retryAfter / 60);
        errorMsg += ` (try again in about ${minutes} minute${minutes === 1 ? '' : 's'})`;
      }
    }

    throw new Error(errorMsg);
  }

  return res.json();
}

async function fetchJSON(endpoint, options = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  return handleResponse(res);
}

// Posts to `endpoint` asking for a `text/event-stream` reply and reads it
// as SSE (`data: {...}\n\n` frames, matching the shape the backend's
// streaming chat endpoints already emit). Each frame is one of
// `{ delta }`, `{ done: true }`, or `{ error }`.
async function streamSSE(endpoint, body, { onDelta, onDone, onError, signal } = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err.name === 'AbortError') return;
    onError?.(err.message || 'Network error');
    return;
  }

  if (!res.ok || !res.body) {
    let errorMsg = `API Error: ${res.status} ${res.statusText}`;
    try {
      const errorData = await res.json();
      if (errorData.detail) errorMsg = errorData.detail;
    } catch (_) {}
    onError?.(errorMsg);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sepIndex;
      while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);

        const dataLine = rawEvent.split('\n').find((line) => line.startsWith('data:'));
        if (!dataLine) continue;
        const jsonStr = dataLine.slice(5).trim();
        if (!jsonStr) continue;

        let payload;
        try {
          payload = JSON.parse(jsonStr);
        } catch (_) {
          continue;
        }

        if (payload.error) {
          onError?.(payload.error);
          return;
        }
        if (payload.delta) {
          onDelta?.(payload.delta);
        }
        if (payload.done) {
          onDone?.();
          return;
        }
      }
    }
    onDone?.();
  } catch (err) {
    if (err.name === 'AbortError') return;
    onError?.(err.message || 'Stream interrupted');
  }
}

export const api = {
  // Auth
  requestSignupOtp: ({ email, password, name }) =>
    fetchJSON('/auth/signup/request-otp', { method: 'POST', body: JSON.stringify({ email, password, name }) }),
  verifySignupOtp: ({ email, otp }) =>
    fetchJSON('/auth/signup/verify-otp', { method: 'POST', body: JSON.stringify({ email, otp }) }),
  login: ({ email, password }) =>
    fetchJSON('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  loginWithGoogle: (credential) =>
    fetchJSON('/auth/google', { method: 'POST', body: JSON.stringify({ credential }) }),
  logout: () => fetchJSON('/auth/logout', { method: 'POST' }),
  me: () => fetchJSON('/auth/me'),

  // Profiles
  getProfiles: () => fetchJSON('/profiles'),
  getProfile: (id) => fetchJSON(`/profiles/${id}`),
  deleteProfile: (id) => fetchJSON(`/profiles/${id}`, { method: 'DELETE' }),
  getProfileConversations: (id) => fetchJSON(`/profiles/${id}/conversations`),
  setProfileVoice: (id, gender) =>
    fetchJSON(`/profiles/${id}/voice`, {
      method: 'PUT',
      body: JSON.stringify({ gender }),
    }),

  // Analysis Flow
  startAnalysis: () => fetchJSON('/analyze/start', { method: 'POST' }),
  sendAnalysisMessage: (sessionId, message) =>
    fetchJSON('/analyze/message', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, message }),
    }),
  finalizeAnalysis: (sessionId, profileName) =>
    fetchJSON('/analyze/finalize', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, profile_name: profileName }),
    }),

  // WhatsApp Chat Import Flow
  uploadWhatsAppChat: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/analyze/whatsapp/upload`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    }).then(handleResponse);
  },
  finalizeWhatsAppChat: (uploadId, targetSender, profileName) =>
    fetchJSON('/analyze/whatsapp/finalize', {
      method: 'POST',
      body: JSON.stringify({
        upload_id: uploadId,
        target_sender: targetSender,
        profile_name: profileName,
      }),
    }),

  // Chat Flow
  startChat: (profileId) =>
    fetchJSON('/chat/start', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId }),
    }),
  sendChatMessage: (sessionId, message) =>
    fetchJSON('/chat/message', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, message }),
    }),
  // Streaming variant used by the chat UI: same endpoint, but asks for
  // `text/event-stream` so the reply arrives token-by-token instead of
  // all at once. `callbacks` is { onDelta, onDone, onError, signal }.
  streamChatMessage: (sessionId, message, callbacks) =>
    streamSSE('/chat/message', { session_id: sessionId, message }, callbacks),

  // Reflect / Journaling
  createReflectEntry: (profileId, content) =>
    fetchJSON('/reflect', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, content }),
    }),
  getReflectEntries: (profileId, { limit, skip } = {}) => {
    const params = new URLSearchParams();
    if (profileId) params.set('profile_id', profileId);
    if (limit) params.set('limit', limit);
    if (skip) params.set('skip', skip);
    const qs = params.toString();
    return fetchJSON(`/reflect${qs ? `?${qs}` : ''}`);
  },
  getReflectEntry: (id) => fetchJSON(`/reflect/${id}`),
  updateReflectEntry: (id, content) =>
    fetchJSON(`/reflect/${id}`, { method: 'PATCH', body: JSON.stringify({ content }) }),
  reanalyzeReflectEntry: (id) => fetchJSON(`/reflect/${id}/analyze`, { method: 'POST' }),
  deleteReflectEntry: (id) => fetchJSON(`/reflect/${id}`, { method: 'DELETE' }),

  // Voice Chat Flow (Vapi)
  getVoiceConfig: () => fetchJSON('/voice/config'),
  startVoiceSession: (profileId) =>
    fetchJSON('/voice/start', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId }),
    }),
  endVoiceSession: (sessionId) =>
    fetchJSON('/voice/end', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),
};
