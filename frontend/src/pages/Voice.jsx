import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, MessageCircleWarning, Phone, PhoneOff, Settings, Users } from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Loader from '../components/common/Loader';
import AnimatedBackground from '../components/common/AnimatedBackground';
import ConnectionStatus from '../components/features/voice/ConnectionStatus';
import CallTimer from '../components/features/voice/CallTimer';
import WaveformVisualizer from '../components/features/voice/WaveformVisualizer';
import VoiceTranscript from '../components/features/voice/VoiceTranscript';
import SpeakingIndicator from '../components/features/voice/SpeakingIndicator';
import { useProfile } from '../context/ProfileContext';
import { useVapiCall } from '../hooks/useVapiCall';
import { api } from '../services/api';

export default function Voice() {
  const { selectedProfile } = useProfile();

  const [voiceConfig, setVoiceConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);

  useEffect(() => {
    api
      .getVoiceConfig()
      .then(setVoiceConfig)
      .catch(() => setVoiceConfig({ enabled: false }))
      .finally(() => setConfigLoading(false));
  }, []);

  const {
    status,
    error,
    isAssistantSpeaking,
    isListening,
    volumeLevel,
    transcript,
    callDuration,
    connect,
    disconnect,
  } = useVapiCall(selectedProfile?.id);

  const connected = status === 'connected';
  const busy = status === 'connecting';

  if (!selectedProfile) {
    return (
      <div className="relative min-h-screen bg-[#050505] text-white">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 pt-40 flex flex-col items-center justify-center text-center px-6">
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
            <Users className="w-7 h-7 text-slate-400" />
          </div>
          <h1 className="text-2xl font-bold mb-2">No Twin Selected</h1>
          <p className="text-slate-400 max-w-md mb-6">
            Choose or create a digital twin before starting a voice call.
          </p>
          <Link to="/profiles">
            <Button>Go to Profiles</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (configLoading) {
    return (
      <div className="relative min-h-screen bg-[#050505] text-white">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 pt-40">
          <Loader text="Checking voice configuration..." />
        </div>
      </div>
    );
  }

  if (!voiceConfig?.enabled) {
    return (
      <div className="relative min-h-screen bg-[#050505] text-white">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 pt-40 flex flex-col items-center justify-center text-center px-6">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-4">
            <Settings className="w-7 h-7 text-amber-400" />
          </div>
          <h1 className="text-2xl font-bold mb-2">Voice Chat Isn't Configured Yet</h1>
          <p className="text-slate-400 max-w-lg mb-2">
            {voiceConfig?.reason || 'Voice Chat uses Vapi for real-time speech — see backend/.env.example for setup.'}
          </p>
          <p className="text-slate-500 text-xs max-w-lg mb-6">
            After editing <code className="text-slate-300 bg-white/5 px-1.5 py-0.5 rounded">backend/.env</code>,
            restart the backend server for changes to take effect.
          </p>
          <Link to="/chat">
            <Button variant="secondary">Use Text Chat Instead</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#050505] text-white flex flex-col">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 flex-1 flex flex-col max-w-2xl w-full mx-auto pt-28 pb-6 px-4">
        <div className="flex items-center justify-between mb-6 px-1">
          <div>
            <h1 className="font-bold text-white text-lg leading-tight">{selectedProfile.name}</h1>
            <span className="text-xs text-slate-500">Voice Chat</span>
          </div>
          <div className="flex items-center gap-3">
            <CallTimer seconds={callDuration} active={connected} />
            <ConnectionStatus status={status} />
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 mb-4 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            <MessageCircleWarning className="w-4 h-4 shrink-0" />
            <span>{typeof error === 'string' ? error : 'Voice call error.'}</span>
          </div>
        )}

        <div className="bg-[#09090B]/40 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden flex flex-col">
          {/* Presence + Waveform */}
          <div className="pt-10 pb-6 px-6 flex flex-col items-center gap-6 border-b border-white/10">
            <SpeakingIndicator
              twinName={selectedProfile.name}
              isAssistantSpeaking={isAssistantSpeaking}
              isListening={isListening}
              connected={connected}
            />

            <div className="text-center h-6">
              {connected && (
                <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                  {isAssistantSpeaking ? 'Speaking...' : 'Listening...'}
                </span>
              )}
            </div>

            <WaveformVisualizer
              level={isAssistantSpeaking ? volumeLevel : 0.15}
              active={connected}
              color={isAssistantSpeaking ? 'blue' : 'purple'}
            />

            <div>
              {!connected ? (
                <Button
                  size="lg"
                  icon={Phone}
                  loading={busy}
                  disabled={busy}
                  onClick={connect}
                  className="px-10"
                >
                  {status === 'ended' ? 'Call Again' : 'Connect'}
                </Button>
              ) : (
                <Button size="lg" variant="danger" icon={PhoneOff} onClick={disconnect} className="px-10">
                  Disconnect
                </Button>
              )}
            </div>
          </div>

          {/* Live Transcript */}
          <div className="flex flex-col min-h-[220px] max-h-[360px]">
            <VoiceTranscript transcript={transcript} twinInitial={selectedProfile.name} />
          </div>
        </div>

        <div className="flex items-center gap-2 mt-4 px-1 text-xs text-slate-500">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Voice replies are generated from the same analyzed personality as Text Chat.</span>
        </div>
      </div>
    </div>
  );
}
