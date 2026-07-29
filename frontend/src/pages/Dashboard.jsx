import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Sparkles,
  Users,
  Clock,
  Hash,
  BookOpen,
  Brain,
  Heart,
  Compass,
  RefreshCcw,
} from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Loader from '../components/common/Loader';
import AnimatedBackground from '../components/common/AnimatedBackground';
import StatCard from '../components/features/profile/StatCard';
import { useProfile } from '../context/ProfileContext';
import { api } from '../services/api';

function KeyValueGrid({ data }) {
  if (!data || typeof data !== 'object' || Object.keys(data).length === 0) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="bg-white/5 p-3 rounded-xl">
          <span className="text-xs text-slate-400 font-semibold block uppercase">
            {key.replace(/_/g, ' ')}
          </span>
          <span className="text-sm font-medium text-white">
            {Array.isArray(value) ? value.join(', ') : String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const { selectedProfile, fetchProfiles } = useProfile();
  const navigate = useNavigate();

  const [profileData, setProfileData] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    if (!selectedProfile) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [detail, convos] = await Promise.all([
        api.getProfile(selectedProfile.id),
        api.getProfileConversations(selectedProfile.id),
      ]);
      setProfileData(detail);
      setConversations(convos);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProfile]);

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
            Choose or create a digital twin to see its dashboard.
          </p>
          <Link to="/profiles">
            <Button>Go to Profiles</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="relative min-h-screen bg-[#050505] text-white">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 pt-40">
          <Loader text="Loading dashboard..." />
        </div>
      </div>
    );
  }

  const profile = profileData?.profile || {};
  const meta = profileData?.metadata || selectedProfile;
  const llm = profile.llm_analysis || {};
  const comm = profile.communication || {};
  const stats = comm.statistics || {};
  const vocab = comm.writing_patterns?.vocabulary || {};

  return (
    <div className="relative min-h-screen bg-[#050505] text-white pb-20">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 max-w-6xl mx-auto px-6 pt-32">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center text-xl font-bold shadow-[0_0_15px_rgba(79,139,255,0.3)]">
              {meta.name ? meta.name.charAt(0).toUpperCase() : 'T'}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">{meta.name || 'Your Twin'}</h1>
              <span className="text-xs text-slate-500">
                Created {meta.created_at ? new Date(meta.created_at).toLocaleDateString() : '—'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" icon={RefreshCcw} onClick={loadData}>
              Refresh
            </Button>
            <Button icon={MessageSquare} onClick={() => navigate('/mode')}>
              Talk to Twin
            </Button>
            <Link to="/analyze">
              <Button variant="secondary">Create New Twin</Button>
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <StatCard
            icon={MessageSquare}
            label="Conversations"
            value={conversations.length}
            subtext="chat threads"
            color="blue"
          />
          <StatCard
            icon={Hash}
            label="Words Analyzed"
            value={stats.words ?? '—'}
            subtext="from your answers"
            color="purple"
          />
          <StatCard
            icon={Clock}
            label="Last Used"
            value={meta.last_used ? new Date(meta.last_used).toLocaleDateString() : '—'}
            subtext={meta.last_used ? new Date(meta.last_used).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
            color="green"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Personality */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="space-y-5">
              <div className="flex items-center gap-2 pb-4 border-b border-white/10">
                <Brain className="w-5 h-5 text-[#8B5CF6]" />
                <h3 className="font-bold text-white text-lg">Personality</h3>
              </div>
              <KeyValueGrid data={llm.personality} />
              {!llm.personality && (
                <p className="text-sm text-slate-500">No personality data available yet.</p>
              )}
            </Card>

            <Card className="space-y-5">
              <div className="flex items-center gap-2 pb-4 border-b border-white/10">
                <Compass className="w-5 h-5 text-[#4F8BFF]" />
                <h3 className="font-bold text-white text-lg">Thinking & Emotional Style</h3>
              </div>
              <KeyValueGrid data={llm.thinking_pattern} />
              <KeyValueGrid data={llm.emotional_style} />
              <KeyValueGrid data={llm.conversation_behaviour} />
            </Card>

            {llm.interests?.length > 0 && (
              <Card>
                <div className="flex items-center gap-2 pb-4 border-b border-white/10 mb-4">
                  <Heart className="w-5 h-5 text-[#8B5CF6]" />
                  <h3 className="font-bold text-white text-lg">Interests</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {llm.interests.map((topic, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 bg-[#8B5CF6]/10 text-[#8B5CF6] border border-[#8B5CF6]/20 rounded-full text-xs font-medium"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </Card>
            )}

            {llm.summary && (
              <Card>
                <div className="flex items-center gap-2 pb-4 border-b border-white/10 mb-4">
                  <Sparkles className="w-5 h-5 text-[#4F8BFF]" />
                  <h3 className="font-bold text-white text-lg">Summary</h3>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed italic">"{llm.summary}"</p>
              </Card>
            )}
          </div>

          {/* Right: Communication + Conversations */}
          <div className="space-y-6">
            <Card className="space-y-4">
              <div className="flex items-center gap-2 pb-4 border-b border-white/10">
                <BookOpen className="w-5 h-5 text-[#4F8BFF]" />
                <h3 className="font-bold text-white text-lg">Writing Style</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Avg. sentence length</span>
                  <span className="text-white font-medium">
                    {stats.average_sentence_length?.toFixed
                      ? stats.average_sentence_length.toFixed(1)
                      : stats.average_sentence_length ?? '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Vocabulary richness</span>
                  <span className="text-white font-medium">
                    {vocab.lexical_diversity?.toFixed
                      ? vocab.lexical_diversity.toFixed(2)
                      : vocab.lexical_diversity ?? '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Sentences analyzed</span>
                  <span className="text-white font-medium">{stats.sentences ?? '—'}</span>
                </div>
              </div>
            </Card>

            <Card className="space-y-3">
              <div className="flex items-center gap-2 pb-4 border-b border-white/10">
                <MessageSquare className="w-5 h-5 text-[#8B5CF6]" />
                <h3 className="font-bold text-white text-lg">Conversations</h3>
              </div>
              {conversations.length === 0 ? (
                <p className="text-sm text-slate-500">No conversations yet. Start chatting with your twin.</p>
              ) : (
                <div className="space-y-2">
                  {conversations.map((c) => (
                    <div
                      key={c.id}
                      className="flex items-center justify-between bg-white/5 rounded-xl px-3 py-2.5"
                    >
                      <div>
                        <span className="text-sm font-medium text-white block">{c.title}</span>
                        <span className="text-xs text-slate-500">{c.message_count} messages</span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {new Date(c.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <Button className="w-full mt-2" size="sm" onClick={() => navigate('/chat')}>
                Continue Chat
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
