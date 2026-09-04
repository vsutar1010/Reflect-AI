import React, { useState } from 'react';
import { Trash2, Loader2, AlertTriangle } from 'lucide-react';
import Card from '../../common/Card';
import Button from '../../common/Button';
import Modal from '../../common/Modal';
import { moodBadgeClass, formatEntryDate } from './moodStyles';

export default function ReflectEntryCard({ entry, onOpen, onDelete }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const analysis = entry.analysis;
  const status = analysis?.status;

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(entry.id);
      setShowDeleteModal(false);
    } catch (err) {
      setDeleting(false);
      alert('Failed to delete entry: ' + err.message);
    }
  };

  return (
    <>
      <Card hover glow onClick={() => onOpen(entry)} className="cursor-pointer">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-semibold text-slate-400">{formatEntryDate(entry.created_at)}</span>
              {status === 'ready' && analysis?.mood && (
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${moodBadgeClass(analysis.mood)}`}>
                  {analysis.mood}
                </span>
              )}
              {status === 'pending' && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border border-white/10 bg-white/5 text-slate-400 inline-flex items-center gap-1">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" /> Analyzing
                </span>
              )}
              {status === 'failed' && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-400 inline-flex items-center gap-1">
                  <AlertTriangle className="w-2.5 h-2.5" /> Analysis unavailable
                </span>
              )}
            </div>
            <p className="text-sm text-slate-200 leading-relaxed line-clamp-2">{entry.content}</p>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowDeleteModal(true);
            }}
            className="p-2 shrink-0 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-full transition-colors"
            title="Delete entry"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </Card>

      <Modal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)} title="Delete Reflection">
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Are you sure you want to delete this journal entry? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" loading={deleting} onClick={handleDelete}>
              Delete Permanently
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
