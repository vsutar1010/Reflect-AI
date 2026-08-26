const API_BASE = 'http://localhost:8000/api';

async function handleResponse(res) {
  if (!res.ok) {
    let errorMsg = `API Error: ${res.status} ${res.statusText}`;
    try {
      const errorData = await res.json();
      if (errorData.detail) errorMsg = errorData.detail;
    } catch (_) {}
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
