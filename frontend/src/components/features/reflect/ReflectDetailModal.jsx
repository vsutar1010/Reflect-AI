import React, { useEffect, useState } from 'react';
import { AlertTriangle, Pencil, RefreshCcw, Trash2 } from 'lucide-react';
import Button from '../../common/Button';
import Modal from '../../common/Modal';
import { moodBadgeClass, formatEntryDate } from './moodStyles';

const MAX_CONTENT_LENGTH = 8000;

export default function ReflectDetailModal({ entry, onClose, onSave, onReanalyze, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entry?.content || '');
  const [stage, setStage] = useState('idle'); // idle | saving | analyzing
  const [error, setError] = useState(null);
  const [reanalyzing, setReanalyzing] = useState(false);

  useEffect(() => {
    setDraft(entry?.content || '');
    setEditing(false);
    setError(null);
    setStage('idle');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entry?.id]);

  if (!entry) return null;

  const analysis = entry.analysis;
  const status = analysis?.status;

  const handleSaveEdit = async () => {
    const text = draft.trim();
    if (!text) {
      setError('Journal entry cannot be empty.');
      return;
    }
    setError(null);
    setStage('saving');
    const stageTimer = setTimeout(() => setStage('analyzing'), 500);
    try {
      await onSave(entry.id, text);
      setEditing(false);
    } catch (err) {
      setError(err.message || 'Failed to save changes.');
    } finally {
      clearTimeout(stageTimer);
      setStage('idle');
    }
  };

  const handleReanalyze = async () => {
    setReanalyzing(true);
    setError(null);
    try {
      await onReanalyze(entry.id);
    } catch (err) {
      setError(err.message || 'Failed to re-run analysis.');
    } finally {
      setReanalyzing(false);
    }
  };

  return (
    <Modal isOpen={!!entry} onClose={onClose} title="Reflection" maxWidth="max-w-2xl">
      <div className="space-y-6 max-h-[70vh] overflow-y-auto pr-1">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="font-semibold">{formatEntryDate(entry.created_at)}</span>
          {entry.updated_at !== entry.created_at && <span>· edited</span>}
          {status === 'ready' && analysis?.mood && (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${moodBadgeClass(analysis.mood)}`}>
              {analysis.mood}
            </span>
          )}
        </div>

        {error && (
          <div className="px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Original Entry */}
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Original Entry</h4>
          {editing ? (
            <div className="space-y-2">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                maxLength={MAX_CONTENT_LENGTH}
                rows={6}
                className="w-full resize-none bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-[#4F8BFF]/50 transition-all duration-300"
              />
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  {draft.length} / {MAX_CONTENT_LENGTH}
                </span>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={() => { setEditing(false); setDraft(entry.content); setError(null); }}>
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    loading={stage !== 'idle'}
                    onClick={handleSaveEdit}
                  >
                    {stage === 'saving' ? 'Saving...' : stage === 'analyzing' ? 'Analyzing...' : 'Save'}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{entry.content}</p>
          )}
        </div>

        {!editing && (
          <>
            {status === 'failed' && (
              <div className="px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p>AI reflection temporarily unavailable{analysis?.error ? ` (${analysis.error})` : '.'}</p>
                  <Button variant="secondary" size="sm" className="mt-2" icon={RefreshCcw} loading={reanalyzing} onClick={handleReanalyze}>
                    Try analysis again
                  </Button>
                </div>
              </div>
            )}

            {status === 'pending' && (
              <p className="text-sm text-slate-400">Analyzing your entry...</p>
            )}

            {status === 'ready' && (
              <>
                {analysis.themes?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Key Themes</h4>
                    <div className="flex flex-wrap gap-2">
                      {analysis.themes.map((theme, i) => (
                        <span
                          key={i}
                          className="px-3 py-1 bg-[#8B5CF6]/10 text-[#8B5CF6] border border-[#8B5CF6]/20 rounded-full text-xs font-medium"
                        >
                          {theme}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.reflection && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Reflection</h4>
                    <p className="text-sm text-slate-200 leading-relaxed">{analysis.reflection}</p>
                  </div>
                )}

                {analysis.observations && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Observations</h4>
                    <p className="text-sm text-slate-300 leading-relaxed">{analysis.observations}</p>
                  </div>
                )}

                {analysis.next_step && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Next Step</h4>
                    <p className="text-sm text-slate-300 leading-relaxed">{analysis.next_step}</p>
                  </div>
                )}
              </>
            )}

            <div className="flex justify-end gap-3 pt-2 border-t border-white/10">
              <Button variant="ghost" size="sm" icon={Trash2} onClick={() => onDelete(entry.id)}>
                Delete
              </Button>
              <Button variant="secondary" size="sm" icon={Pencil} onClick={() => setEditing(true)}>
                Edit
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
