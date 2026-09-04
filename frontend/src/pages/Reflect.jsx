import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, MessageCircleWarning, Sparkles, Users } from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Loader from '../components/common/Loader';
import AnimatedBackground from '../components/common/AnimatedBackground';
import ReflectEntryCard from '../components/features/reflect/ReflectEntryCard';
import ReflectDetailModal from '../components/features/reflect/ReflectDetailModal';
import { useProfile } from '../context/ProfileContext';
import { api } from '../services/api';

const MAX_CONTENT_LENGTH = 8000;
const PAGE_SIZE = 20;

export default function Reflect() {
  const { selectedProfile } = useProfile();

  const [content, setContent] = useState('');
  const [stage, setStage] = useState('idle'); // idle | saving | analyzing
  const [saveError, setSaveError] = useState(null);
  const [justSaved, setJustSaved] = useState(false);

  const [entries, setEntries] = useState([]);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [listError, setListError] = useState(null);

  const [selectedEntry, setSelectedEntry] = useState(null);

  const loadEntries = async () => {
    if (!selectedProfile) return;
    setLoadingEntries(true);
    setListError(null);
    try {
      const list = await api.getReflectEntries(selectedProfile.id, { limit: PAGE_SIZE });
      setEntries(list);
      setHasMore(list.length === PAGE_SIZE);
    } catch (err) {
      setListError(err.message || 'Failed to load your reflections.');
    } finally {
      setLoadingEntries(false);
    }
  };

  useEffect(() => {
    setEntries([]);
    setSelectedEntry(null);
    loadEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProfile]);

  const loadMore = async () => {
    if (!selectedProfile || loadingMore) return;
    setLoadingMore(true);
    try {
      const more = await api.getReflectEntries(selectedProfile.id, { limit: PAGE_SIZE, skip: entries.length });
      setEntries((prev) => [...prev, ...more]);
      setHasMore(more.length === PAGE_SIZE);
    } catch (err) {
      setListError(err.message || 'Failed to load more reflections.');
    } finally {
      setLoadingMore(false);
    }
  };

  const handleSave = async () => {
    const text = content.trim();
    if (!text || !selectedProfile || stage !== 'idle') return;

    setSaveError(null);
    setJustSaved(false);
    setStage('saving');
    // The backend saves the entry and runs AI analysis in one request —
    // this timer just gives the two-phase feedback the flow implies
    // ("Saving..." then "Analyzing...") without a second round trip.
    const stageTimer = setTimeout(() => setStage('analyzing'), 600);

    try {
      const entry = await api.createReflectEntry(selectedProfile.id, text);
      setEntries((prev) => [entry, ...prev]);
      setContent('');
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 4000);
    } catch (err) {
      setSaveError(err.message || 'Failed to save your reflection.');
    } finally {
      clearTimeout(stageTimer);
      setStage('idle');
    }
  };

  const updateEntryInPlace = (id, updated) => {
    setEntries((prev) => prev.map((e) => (e.id === id ? updated : e)));
    setSelectedEntry((prev) => (prev && prev.id === id ? updated : prev));
  };

  const handleEditSave = async (id, newContent) => {
    const updated = await api.updateReflectEntry(id, newContent);
    updateEntryInPlace(id, updated);
  };

  const handleReanalyze = async (id) => {
    const updated = await api.reanalyzeReflectEntry(id);
    updateEntryInPlace(id, updated);
  };

  const handleDeleteEntry = async (id) => {
    await api.deleteReflectEntry(id);
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  const handleDeleteFromModal = async (id) => {
    if (!window.confirm('Delete this journal entry? This cannot be undone.')) return;
    try {
      await handleDeleteEntry(id);
      setSelectedEntry(null);
    } catch (err) {
      alert('Failed to delete entry: ' + err.message);
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
            Choose or create a digital twin before writing a reflection.
          </p>
          <Link to="/profiles">
            <Button>Go to Profiles</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#050505] text-white pb-24">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 max-w-3xl mx-auto px-6 pt-32">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-2xl bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 text-[#8B5CF6] flex items-center justify-center">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Reflect</h1>
            <p className="text-sm text-slate-400">Journal your thoughts and let your twin reflect them back.</p>
          </div>
        </div>

        {/* Compose */}
        <Card className="mb-10 space-y-3">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            maxLength={MAX_CONTENT_LENGTH}
            disabled={stage !== 'idle'}
            rows={6}
            placeholder={"What's on your mind?\n\nWrite about your day, thoughts, feelings, experiences, or anything you want to reflect on..."}
            className="w-full resize-none bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-[#4F8BFF]/50 focus:shadow-[0_0_15px_rgba(79,139,255,0.15)] transition-all duration-300 disabled:opacity-60"
          />

          <div className="flex items-center justify-between">
            <span className={`text-xs ${content.length > MAX_CONTENT_LENGTH * 0.95 ? 'text-amber-400' : 'text-slate-500'}`}>
              {content.length} / {MAX_CONTENT_LENGTH}
            </span>
            <Button
              icon={stage === 'idle' ? Sparkles : undefined}
              loading={stage !== 'idle'}
              disabled={!content.trim()}
              onClick={handleSave}
            >
              {stage === 'saving' ? 'Saving...' : stage === 'analyzing' ? 'Analyzing your entry...' : 'Save & Reflect'}
            </Button>
          </div>

          {saveError && (
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              <MessageCircleWarning className="w-4 h-4 shrink-0" />
              <span>{saveError}</span>
            </div>
          )}

          {justSaved && (
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Reflection ready ✓</span>
            </div>
          )}
        </Card>

        {/* History */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white">Your Reflections</h2>
          <span className="text-xs text-slate-500">{entries.length} entr{entries.length === 1 ? 'y' : 'ies'}</span>
        </div>

        {listError && (
          <div className="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            <MessageCircleWarning className="w-4 h-4 shrink-0" />
            <span>{listError}</span>
          </div>
        )}

        {loadingEntries ? (
          <Loader text="Loading your reflections..." />
        ) : entries.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-10">
            No reflections yet. Write your first one above.
          </p>
        ) : (
          <div className="space-y-3">
            {entries.map((entry) => (
              <ReflectEntryCard
                key={entry.id}
                entry={entry}
                onOpen={setSelectedEntry}
                onDelete={handleDeleteEntry}
              />
            ))}
          </div>
        )}

        {hasMore && !loadingEntries && (
          <div className="flex justify-center mt-6">
            <Button variant="secondary" size="sm" loading={loadingMore} onClick={loadMore}>
              Load more
            </Button>
          </div>
        )}
      </div>

      <ReflectDetailModal
        entry={selectedEntry}
        onClose={() => setSelectedEntry(null)}
        onSave={handleEditSave}
        onReanalyze={handleReanalyze}
        onDelete={handleDeleteFromModal}
      />
    </div>
  );
}
