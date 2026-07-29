import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircleWarning, RefreshCcw, Users } from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Loader from '../components/common/Loader';
import AnimatedBackground from '../components/common/AnimatedBackground';
import MessageList from '../components/features/chat/MessageList';
import ChatInput from '../components/features/chat/ChatInput';
import { useProfile } from '../context/ProfileContext';
import { api } from '../services/api';

export default function Chat() {
  const { selectedProfile } = useProfile();

  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [loadingSession, setLoadingSession] = useState(true);
  const [error, setError] = useState(null);

  const startedForProfile = useRef(null);

  useEffect(() => {
    if (!selectedProfile) {
      setLoadingSession(false);
      return;
    }
    if (startedForProfile.current === selectedProfile.id) return;
    startedForProfile.current = selectedProfile.id;

    async function startSession() {
      setLoadingSession(true);
      setError(null);
      try {
        const res = await api.startChat(selectedProfile.id);
        setSessionId(res.session_id);

        if (res.history && res.history.length > 0) {
          // Resume the existing conversation instead of showing the
          // canned greeting again.
          setMessages(
            res.history.map((m) => ({
              role: m.role,
              content: m.content,
              timestamp: Date.now(),
            }))
          );
        } else {
          setMessages([
            { role: 'assistant', content: res.message, timestamp: Date.now() },
          ]);
        }
      } catch (err) {
        setError(err.message || 'Failed to start chat session.');
      } finally {
        setLoadingSession(false);
      }
    }

    startSession();
  }, [selectedProfile]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !sessionId || isTyping) return;

    setMessages((prev) => [...prev, { role: 'user', content: text, timestamp: Date.now() }]);
    setInput('');
    setIsTyping(true);
    setError(null);

    try {
      const res = await api.sendChatMessage(sessionId, text);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.reply, timestamp: Date.now() },
      ]);
    } catch (err) {
      setError(err.message || 'Failed to get a reply. Is Ollama running?');
    } finally {
      setIsTyping(false);
    }
  };

  const restartSession = () => {
    startedForProfile.current = null;
    setSessionId(null);
    setMessages([]);
    setError(null);
    if (selectedProfile) {
      startedForProfile.current = selectedProfile.id;
      setLoadingSession(true);
      api
        .startChat(selectedProfile.id)
        .then((res) => {
          setSessionId(res.session_id);
          if (res.history && res.history.length > 0) {
            setMessages(
              res.history.map((m) => ({
                role: m.role,
                content: m.content,
                timestamp: Date.now(),
              }))
            );
          } else {
            setMessages([{ role: 'assistant', content: res.message, timestamp: Date.now() }]);
          }
        })
        .catch((err) => setError(err.message || 'Failed to start chat session.'))
        .finally(() => setLoadingSession(false));
    }
  };

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
            Choose or create a digital twin before starting a conversation.
          </p>
          <Link to="/profiles">
            <Button>Go to Profiles</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#050505] text-white flex flex-col">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 flex-1 flex flex-col max-w-3xl w-full mx-auto pt-28 pb-6 px-4 h-screen">
        <div className="flex items-center justify-between mb-4 px-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center font-bold text-white shadow-[0_0_10px_rgba(79,139,255,0.4)]">
              {selectedProfile.name ? selectedProfile.name.charAt(0).toUpperCase() : 'T'}
            </div>
            <div>
              <h1 className="font-bold text-white leading-tight">{selectedProfile.name}</h1>
              <span className="text-xs text-slate-500">Your digital twin</span>
            </div>
          </div>
          <Button variant="ghost" size="sm" icon={RefreshCcw} onClick={restartSession}>
            Restart
          </Button>
        </div>

        {error && (
          <div className="flex items-center gap-2 mb-3 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            <MessageCircleWarning className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex-1 flex flex-col bg-[#09090B]/40 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden">
          {loadingSession ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader text="Waking up your twin..." />
            </div>
          ) : (
            <MessageList
              messages={messages}
              isTyping={isTyping}
              twinInitial={selectedProfile.name}
            />
          )}

          <ChatInput
            value={input}
            onChange={setInput}
            onSend={handleSend}
            disabled={loadingSession || isTyping || !sessionId}
          />
        </div>
      </div>
    </div>
  );
}
