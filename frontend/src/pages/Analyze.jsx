import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Sparkles,
  CheckCircle2,
  User,
  RefreshCw,
  AlertCircle,
  MessageSquareText,
  Upload,
  FileText,
  ArrowLeft,
} from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Loader from '../components/common/Loader';
import AnimatedBackground from '../components/common/AnimatedBackground';
import ProgressCard from '../components/features/analysis/ProgressCard';
import QuestionCard from '../components/features/analysis/QuestionCard';
import AnalysisSidebar from '../components/features/analysis/AnalysisSidebar';
import { api } from '../services/api';
import { useProfile } from '../context/ProfileContext';

// Frontend-only UX check, purely to avoid an unnecessary upload attempt
// and give immediate feedback — must be kept in sync with the backend's
// MAX_WHATSAPP_UPLOAD_SIZE_MB default (backend/app/config.py). The
// backend enforces its own configured limit independently and is the
// only real security boundary; if an operator changes the backend's
// env var without updating this constant, uploads stay just as safe —
// only this early warning would be briefly out of sync with it.
const MAX_WHATSAPP_UPLOAD_MB = 15;
const MAX_WHATSAPP_UPLOAD_BYTES = MAX_WHATSAPP_UPLOAD_MB * 1024 * 1024;

export default function Analyze() {
  const navigate = useNavigate();
  const { fetchProfiles, selectProfile } = useProfile();

  // Which on-ramp the user picked: null (choosing) | 'interview' | 'whatsapp'
  const [mode, setMode] = useState(null);

  // Interview Flow State
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // Shared "twin created" state — both flows land here
  const [isCompleted, setIsCompleted] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [profileName, setProfileName] = useState('');

  // Status & Form State
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // WhatsApp Import Flow State
  const [waStep, setWaStep] = useState('idle'); // idle | uploading | picking
  const [waUploadId, setWaUploadId] = useState(null);
  const [waParticipants, setWaParticipants] = useState([]);
  const [waSummary, setWaSummary] = useState(null);
  const [waTargetSender, setWaTargetSender] = useState(null);
  const [waNameInput, setWaNameInput] = useState('');
  const fileInputRef = useRef(null);

  // Total questions count (10)
  const TOTAL_QUESTIONS = 10;

  const resetToModeSelect = () => {
    setMode(null);
    setError(null);
    setIsCompleted(false);
    setFinalizing(false);
    setSessionId(null);
    setWaStep('idle');
    setWaUploadId(null);
    setWaParticipants([]);
    setWaSummary(null);
    setWaTargetSender(null);
    setWaNameInput('');
  };

  // ============================================================
  // Interview Flow
  // ============================================================

  const startNewSession = async () => {
    setLoading(true);
    setError(null);
    setIsCompleted(false);
    setCurrentQuestionIndex(0);
    setProgress(0);
    setProfileName('');

    try {
      const data = await api.startAnalysis();
      setSessionId(data.session_id);
      setQuestion(data.message);
    } catch (err) {
      console.error('Failed to start analysis:', err);
      setError('Unable to start analysis session. Please check if your FastAPI backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const chooseInterview = () => {
    setMode('interview');
    startNewSession();
  };

  const handleAnswerSubmit = async (answerText) => {
    if (!sessionId || submitting) return;
    setSubmitting(true);
    setError(null);

    try {
      const data = await api.sendAnalysisMessage(sessionId, answerText);

      // Check completion
      if (data.progress >= 100 || !data.question) {
        setIsCompleted(true);
        setProgress(100);
        finalizeProfile();
      } else {
        setQuestion(data.question);
        setProgress(data.progress || Math.round(((currentQuestionIndex + 1) / TOTAL_QUESTIONS) * 100));
        setCurrentQuestionIndex((prev) => prev + 1);
      }
    } catch (err) {
      console.error('Failed to submit answer:', err);
      setError(err.message || 'Failed to submit response. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const finalizeProfile = async () => {
    if (!sessionId) return;
    setFinalizing(true);
    setError(null);

    try {
      // No profile_name passed — backend extracts the person's name from
      // their answers and uses it automatically.
      const res = await api.finalizeAnalysis(sessionId, null);
      const twinName = res?.profile_name || 'My Twin';
      setProfileName(twinName);

      await fetchProfiles();

      if (res && res.profile_id) {
        selectProfile({
          id: res.profile_id,
          name: twinName,
          created_at: new Date().toISOString(),
          last_used: new Date().toISOString(),
          conversation_count: 0,
        });
      }

      navigate('/mode');
    } catch (err) {
      console.error('Failed to finalize profile:', err);
      setError(err.message || 'Failed to finalize profile. Please try again.');
    } finally {
      setFinalizing(false);
    }
  };

  // ============================================================
  // WhatsApp Import Flow
  // ============================================================

  const uploadWaFile = async (file) => {
    if (file.size > MAX_WHATSAPP_UPLOAD_BYTES) {
      setError(
        `This WhatsApp export is too large. Maximum allowed size is ${MAX_WHATSAPP_UPLOAD_MB} MB.`
      );
      return;
    }

    setWaStep('uploading');
    setError(null);

    try {
      const res = await api.uploadWhatsAppChat(file);
      setWaUploadId(res.upload_id);
      setWaParticipants(res.participants || []);
      setWaSummary(res);
      setWaStep('picking');
    } catch (err) {
      console.error('Failed to upload chat:', err);
      setError(err.message || 'Failed to parse this chat export.');
      setWaStep('idle');
    }
  };

  const handleWaFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) uploadWaFile(file);
    e.target.value = '';
  };

  const handleWaDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) uploadWaFile(file);
  };

  const chooseWaParticipant = (name) => {
    setWaTargetSender(name);
    setWaNameInput(name);
  };

  const resetWaUpload = () => {
    setWaStep('idle');
    setWaUploadId(null);
    setWaParticipants([]);
    setWaSummary(null);
    setWaTargetSender(null);
    setWaNameInput('');
  };

  const handleWaFinalize = async () => {
    if (!waUploadId || !waTargetSender) return;
    setIsCompleted(true);
    setFinalizing(true);
    setError(null);

    try {
      const res = await api.finalizeWhatsAppChat(waUploadId, waTargetSender, waNameInput);
      const twinName = res?.profile_name || waTargetSender;
      setProfileName(twinName);

      await fetchProfiles();

      if (res && res.profile_id) {
        selectProfile({
          id: res.profile_id,
          name: twinName,
          created_at: new Date().toISOString(),
          last_used: new Date().toISOString(),
          conversation_count: 0,
        });
      }

      navigate('/mode');
    } catch (err) {
      console.error('Failed to finalize WhatsApp twin:', err);
      setError(err.message || 'Failed to build a twin from this chat. Please try again.');
      setIsCompleted(false);
    } finally {
      setFinalizing(false);
    }
  };

  // ============================================================
  // Header copy per mode
  // ============================================================

  const headerCopy = {
    null: {
      badge: 'Neural Cloning Protocol',
      title: 'Create Your Digital Twin',
      subtitle: 'Choose how you’d like to build it — answer a short interview, or import a real WhatsApp conversation.',
    },
    interview: {
      badge: 'Neural Cloning Protocol',
      title: 'Personality Analysis Interview',
      subtitle:
        'Answer 10 natural questions. Our analyzer will measure punctuation patterns, sentence lengths, tone variations, and preferred topics to build your digital double.',
    },
    whatsapp: {
      badge: 'Neural Cloning Protocol',
      title: 'Import a WhatsApp Chat',
      subtitle:
        'Upload a 1:1 WhatsApp export. We analyze how that person actually texts — vocabulary, slang, emoji, reply length — to build a twin of them, not a copy of their messages.',
    },
  };
  const copy = headerCopy[mode ?? 'null'];

  return (
    <div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] font-sans pb-24">
      <AnimatedBackground />

      <Navbar />

      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-36">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-10 border-b border-white/10 pb-8">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 text-xs font-semibold text-[#8B5CF6] uppercase mb-3">
              <Sparkles className="w-3.5 h-3.5" /> {copy.badge}
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">{copy.title}</h1>
            <p className="text-slate-400 text-sm mt-2 max-w-xl">{copy.subtitle}</p>
          </div>

          {mode !== null && (
            <div className="flex gap-3">
              <Button
                variant="secondary"
                size="md"
                icon={ArrowLeft}
                disabled={loading || submitting || finalizing || waStep === 'uploading'}
                onClick={resetToModeSelect}
              >
                Change Method
              </Button>
              {mode === 'interview' && (
                <Button
                  variant="secondary"
                  size="md"
                  icon={RefreshCw}
                  disabled={loading || submitting || finalizing}
                  onClick={startNewSession}
                >
                  Restart Session
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-8 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {mode === null ? (
          /* ============================================================
             Mode Select
             ============================================================ */
          <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card hover glow onClick={chooseInterview} className="cursor-pointer text-center p-8 space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-[#8B5CF6]/10 border border-[#8B5CF6]/30 flex items-center justify-center mx-auto">
                <Sparkles className="w-6 h-6 text-[#8B5CF6]" />
              </div>
              <h3 className="text-lg font-bold text-white">Answer 10 Questions</h3>
              <p className="text-sm text-slate-400">
                A short guided interview about you. We analyze how you answer to build your twin.
              </p>
            </Card>

            <Card
              hover
              glow
              onClick={() => setMode('whatsapp')}
              className="cursor-pointer text-center p-8 space-y-4"
            >
              <div className="w-14 h-14 rounded-2xl bg-[#22C55E]/10 border border-[#22C55E]/30 flex items-center justify-center mx-auto">
                <MessageSquareText className="w-6 h-6 text-[#22C55E]" />
              </div>
              <h3 className="text-lg font-bold text-white">Upload WhatsApp Chat</h3>
              <p className="text-sm text-slate-400">
                Import a real 1:1 WhatsApp export and build a twin of how that person actually texts.
              </p>
            </Card>
          </div>
        ) : isCompleted ? (
          /* ============================================================
             Shared "Twin Created" Screen
             ============================================================ */
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-2xl mx-auto my-8"
          >
            <Card className="text-center p-8 space-y-6">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto shadow-[0_0_20px_rgba(16,185,129,0.2)]">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-white">
                  {mode === 'whatsapp' ? 'Chat Imported!' : 'Interview Complete!'}
                </h2>
                <p className="text-sm text-slate-400 leading-relaxed max-w-md mx-auto">
                  {finalizing
                    ? mode === 'whatsapp'
                      ? 'Analyzing the conversation and building your digital twin...'
                      : 'Building your digital twin from your answers and detecting your name...'
                    : `Your twin${profileName ? ` "${profileName}"` : ''} is ready.`}
                </p>
              </div>

              {finalizing ? (
                <Loader text="Generating personality profile..." />
              ) : (
                <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
                  <User className="w-4 h-4" />
                  <span>{profileName}</span>
                </div>
              )}
            </Card>
          </motion.div>
        ) : mode === 'interview' ? (
          /* ============================================================
             Interview Flow
             ============================================================ */
          loading ? (
            <Loader text="Connecting to Ollama & initializing interview session..." />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              <div className="lg:col-span-8 space-y-6">
                <ProgressCard
                  progress={progress}
                  currentQuestion={currentQuestionIndex + 1}
                  totalQuestions={TOTAL_QUESTIONS}
                />

                <QuestionCard
                  question={question}
                  onSubmit={handleAnswerSubmit}
                  loading={submitting}
                  questionIndex={currentQuestionIndex}
                />
              </div>

              <div className="lg:col-span-4">
                <AnalysisSidebar
                  currentStep={currentQuestionIndex}
                  totalSteps={TOTAL_QUESTIONS}
                  answersCount={currentQuestionIndex}
                />
              </div>
            </div>
          )
        ) : (
          /* ============================================================
             WhatsApp Import Flow
             ============================================================ */
          <div>
            {waStep === 'idle' && (
              <Card className="max-w-2xl mx-auto p-10 text-center space-y-5">
                <div className="w-16 h-16 rounded-2xl bg-[#22C55E]/10 border border-[#22C55E]/30 flex items-center justify-center mx-auto">
                  <Upload className="w-7 h-7 text-[#22C55E]" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white mb-1">Upload a WhatsApp Chat Export</h2>
                  <p className="text-sm text-slate-400 max-w-md mx-auto">
                    In WhatsApp: open the chat &rarr; ⋮ menu &rarr; More &rarr; Export chat &rarr; Without Media.
                    Upload the resulting .txt file below. 1:1 chats only for now.
                  </p>
                  <p className="text-xs text-slate-500 mt-2">Maximum file size: {MAX_WHATSAPP_UPLOAD_MB} MB</p>
                </div>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleWaDrop}
                  className="border-2 border-dashed border-white/15 hover:border-[#22C55E]/40 rounded-2xl py-10 cursor-pointer transition-colors"
                >
                  <FileText className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <p className="text-sm text-slate-400">Click to browse or drag a .txt file here</p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt"
                  className="hidden"
                  onChange={handleWaFileInput}
                />
              </Card>
            )}

            {waStep === 'uploading' && <Loader text="Parsing chat export..." />}

            {waStep === 'picking' && (
              <Card className="max-w-2xl mx-auto p-8 space-y-6">
                <div>
                  <h2 className="text-xl font-bold text-white mb-1">Who should this twin be?</h2>
                  <p className="text-sm text-slate-400">
                    Found {waSummary?.total_messages ?? 0} real messages
                    {waSummary?.system_messages_skipped
                      ? `, skipped ${waSummary.system_messages_skipped} system messages`
                      : ''}
                    {waSummary?.media_messages_skipped ? `, ${waSummary.media_messages_skipped} media` : ''}
                    {waSummary?.deleted_messages_skipped ? `, ${waSummary.deleted_messages_skipped} deleted` : ''}.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {waParticipants.map((p) => (
                    <button
                      key={p.name}
                      onClick={() => chooseWaParticipant(p.name)}
                      className={`text-left p-4 rounded-xl border transition-colors ${
                        waTargetSender === p.name
                          ? 'border-[#22C55E]/60 bg-[#22C55E]/10'
                          : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                      }`}
                    >
                      <div className="font-semibold text-white">{p.name}</div>
                      <div className="text-xs text-slate-400">{p.message_count} messages</div>
                    </button>
                  ))}
                </div>

                {waTargetSender && (
                  <div>
                    <label className="text-xs text-slate-400 mb-1.5 block">Twin name</label>
                    <input
                      value={waNameInput}
                      onChange={(e) => setWaNameInput(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-[#22C55E]/50"
                    />
                  </div>
                )}

                <div className="flex gap-3">
                  <Button variant="secondary" onClick={resetWaUpload}>
                    Choose Different File
                  </Button>
                  <Button disabled={!waTargetSender} onClick={handleWaFinalize} className="flex-1">
                    Create Twin
                  </Button>
                </div>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
