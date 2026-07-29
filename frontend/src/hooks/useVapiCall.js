import { useCallback, useEffect, useRef, useState } from 'react';
import VapiImport from '@vapi-ai/web';
import { api } from '../services/api';

// @vapi-ai/web is CJS-only with `exports.default = Vapi`. Depending on
// how it gets pre-bundled, Vite sometimes double-wraps that so the
// default import resolves to `{ default: Vapi }` instead of the class
// itself, throwing "Vapi is not a constructor". This unwraps either shape.
const Vapi = VapiImport?.default || VapiImport;

/**
 * Vapi/Daily error events aren't always plain strings — sometimes a
 * string, sometimes an Error, sometimes a nested { error: { msg } }
 * object. Rendering whatever comes through directly into JSX crashes
 * React ("Objects are not valid as a React child"), so every path here
 * normalizes to a plain string first.
 */
function toErrorMessage(err, fallback) {
  if (!err) return fallback;
  if (typeof err === 'string') return err;
  if (err instanceof Error) return err.message || fallback;

  const known =
    err.message ||
    err.msg ||
    err.errorMsg ||
    err.error?.message ||
    err.error?.msg ||
    (typeof err.error === 'string' ? err.error : null);

  if (known) return known;

  // Unknown object shape — never let a raw object reach setState/JSX.
  try {
    return JSON.stringify(err);
  } catch {
    return fallback;
  }
}

/**
 * Wraps the Vapi Web SDK's call lifecycle into a small state machine a
 * component can render directly, and syncs session start/end with the
 * backend (which builds the assistant config from the same
 * DigitalTwinEngine that powers Text Chat).
 *
 * status: 'idle' | 'connecting' | 'connected' | 'ended' | 'error'
 */
export function useVapiCall(profileId) {
  const vapiRef = useRef(null);
  const sessionIdRef = useRef(null);
  const timerRef = useRef(null);

  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const [isAssistantSpeaking, setIsAssistantSpeaking] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0);
  const [micLevel, setMicLevel] = useState(0);
  const [transcript, setTranscript] = useState([]);
  const [callDuration, setCallDuration] = useState(0);

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const teardownVapi = useCallback(() => {
    if (vapiRef.current) {
      vapiRef.current.removeAllListeners();
      vapiRef.current = null;
    }
  }, []);

  const endBackendSession = useCallback(() => {
    if (sessionIdRef.current) {
      api.endVoiceSession(sessionIdRef.current).catch(() => {});
      sessionIdRef.current = null;
    }
  }, []);

  const connect = useCallback(async () => {
    if (!profileId) {
      setError('No twin selected.');
      setStatus('error');
      return;
    }

    setStatus('connecting');
    setError(null);
    setTranscript([]);
    setCallDuration(0);

    try {
      const res = await api.startVoiceSession(profileId);
      sessionIdRef.current = res.session_id;

      // Seed the transcript with the greeting immediately — it's already
      // known and about to be spoken, no need to wait for an echo event.
      if (res.assistant?.firstMessage) {
        setTranscript([{ role: 'assistant', text: res.assistant.firstMessage, final: true }]);
      }

      const vapi = new Vapi(res.public_key);
      vapiRef.current = vapi;

      vapi.on('call-start', () => {
        setStatus('connected');
        clearTimer();
        timerRef.current = setInterval(() => setCallDuration((d) => d + 1), 1000);
      });

      vapi.on('call-end', () => {
        setStatus('ended');
        setIsAssistantSpeaking(false);
        setVolumeLevel(0);
        setMicLevel(0);
        clearTimer();
        endBackendSession();
      });

      vapi.on('speech-start', () => setIsAssistantSpeaking(true));
      vapi.on('speech-end', () => setIsAssistantSpeaking(false));
      vapi.on('volume-level', (level) => setVolumeLevel(level));
      vapi.on('local-volume-level', (level) => setMicLevel(level));

      vapi.on('message', (message) => {
        if (message?.type !== 'transcript') return;

        setTranscript((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          const isContinuation = last && last.role === message.role && !last.final;

          const entry = {
            role: message.role,
            text: message.transcript,
            final: message.transcriptType === 'final',
          };

          if (isContinuation) {
            next[next.length - 1] = entry;
          } else {
            next.push(entry);
          }
          return next;
        });
      });

      vapi.on('call-start-failed', (event) => {
        setStatus('error');
        setError(toErrorMessage(event?.error, 'Could not connect the call.'));
      });

      vapi.on('error', (err) => {
        setStatus('error');
        setError(toErrorMessage(err, 'Voice call error.'));
        clearTimer();
      });

      await vapi.start(res.assistant);
    } catch (err) {
      setStatus('error');
      setError(toErrorMessage(err, 'Failed to start voice call.'));
      endBackendSession();
    }
  }, [profileId, endBackendSession]);

  const disconnect = useCallback(() => {
    if (vapiRef.current) {
      vapiRef.current.stop();
    } else {
      endBackendSession();
      setStatus('ended');
    }
    clearTimer();
  }, [endBackendSession]);

  useEffect(() => {
    return () => {
      clearTimer();
      if (vapiRef.current) {
        vapiRef.current.stop();
      }
      teardownVapi();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isListening = status === 'connected' && !isAssistantSpeaking;

  return {
    status,
    error,
    isAssistantSpeaking,
    isListening,
    volumeLevel,
    micLevel,
    transcript,
    callDuration,
    connect,
    disconnect,
  };
}
