import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, CheckCircle2, User, ArrowRight, RefreshCw, AlertCircle } from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Card from '../components/common/Card';
import Loader from '../components/common/Loader';
import ProgressCard from '../components/features/analysis/ProgressCard';
import QuestionCard from '../components/features/analysis/QuestionCard';
import AnalysisSidebar from '../components/features/analysis/AnalysisSidebar';
import { api } from '../services/api';
import { useProfile } from '../context/ProfileContext';

export default function Analyze() {
  const navigate = useNavigate();
  const { fetchProfiles, selectProfile } = useProfile();

  // Analysis State
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);

  // Status & Form State
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [profileName, setProfileName] = useState('');
  const [error, setError] = useState(null);

  // Total questions count (10)
  const TOTAL_QUESTIONS = 10;

  // Initialize analysis session on mount
  useEffect(() => {
    startNewSession();
  }, []);

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

  const handleFinalize = async (e) => {
    e?.preventDefault();
    if (!sessionId || !profileName.trim() || finalizing) return;

    setFinalizing(true);
    setError(null);

    try {
      const res = await api.finalizeAnalysis(sessionId, profileName.trim());
      // Refresh context profiles
      await fetchProfiles();

      // If backend returned profile_id, select it
      if (res && res.profile_id) {
        selectProfile({
          id: res.profile_id,
          name: profileName.trim(),
          created_at: new Date().toISOString(),
          last_used: new Date().toISOString(),
          conversation_count: 0,
        });
      }

      // Navigate to dashboard
      navigate('/dashboard');
    } catch (err) {
      console.error('Failed to finalize profile:', err);
      setError(err.message || 'Failed to finalize profile. Please try again.');
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] font-sans pb-24">
      {/* Background Glows */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[#4F8BFF]/10 blur-[150px]" />
        <div className="absolute top-[20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[#8B5CF6]/10 blur-[150px]" />
      </div>

      <Navbar />

      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-36">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-10 border-b border-white/10 pb-8">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 text-xs font-semibold text-[#8B5CF6] uppercase mb-3">
              <Sparkles className="w-3.5 h-3.5" /> Neural Cloning Protocol
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
              Personality Analysis Interview
            </h1>
            <p className="text-slate-400 text-sm mt-2 max-w-xl">
              Answer 10 natural questions. Our analyzer will measure punctuation patterns, sentence lengths, tone variations, and preferred topics to build your digital double.
            </p>
          </div>

          <Button
            variant="secondary"
            size="md"
            icon={RefreshCw}
            disabled={loading || submitting || finalizing}
            onClick={startNewSession}
          >
            Restart Session
          </Button>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-8 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading Initial Session */}
        {loading ? (
          <Loader text="Connecting to Ollama & initializing interview session..." />
        ) : isCompleted ? (
          /* Finalization Screen */
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
                <h2 className="text-2xl font-bold text-white">Interview Complete!</h2>
                <p className="text-sm text-slate-400 leading-relaxed max-w-md mx-auto">
                  Your 10 responses have been processed into a custom personality profile. Give your digital twin a name to save it.
                </p>
              </div>

              <form onSubmit={handleFinalize} className="space-y-4 text-left max-w-md mx-auto pt-2">
                <Input
                  label="Digital Twin Name"
                  id="profileName"
                  placeholder="e.g. Tanmay, Digital Twin Alpha, Personal Assistant"
                  icon={User}
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  autoFocus
                  required
                />

                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  className="w-full justify-center mt-4"
                  loading={finalizing}
                  disabled={!profileName.trim()}
                  icon={ArrowRight}
                >
                  Generate & Save Twin
                </Button>
              </form>
            </Card>
          </motion.div>
        ) : (
          /* Main Question & Progress Layout */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-8 space-y-6">
              {/* Progress Card */}
              <ProgressCard
                progress={progress}
                currentQuestion={currentQuestionIndex + 1}
                totalQuestions={TOTAL_QUESTIONS}
              />

              {/* Question Card */}
              <QuestionCard
                question={question}
                onSubmit={handleAnswerSubmit}
                loading={submitting}
                questionIndex={currentQuestionIndex}
              />
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-4">
              <AnalysisSidebar
                currentStep={currentQuestionIndex}
                totalSteps={TOTAL_QUESTIONS}
                answersCount={currentQuestionIndex}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
