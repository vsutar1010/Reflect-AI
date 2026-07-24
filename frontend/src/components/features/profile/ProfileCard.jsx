import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { User, Calendar, MessageSquare, Trash2, CheckCircle2, ArrowRight } from 'lucide-react';
import Card from '../../common/Card';
import Button from '../../common/Button';
import Modal from '../../common/Modal';

export default function ProfileCard({ profile, isActive, onSelect, onDelete }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    try {
      return new Date(isoString).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch (_) {
      return isoString;
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(profile.id);
      setShowDeleteModal(false);
    } catch (err) {
      alert('Failed to delete profile: ' + err.message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <Card
        glow={isActive}
        className={`flex flex-col justify-between h-full border ${
          isActive ? 'border-[#4F8BFF] bg-[#4F8BFF]/5 shadow-[0_0_20px_rgba(79,139,255,0.15)]' : 'hover:border-white/20'
        }`}
      >
        <div>
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center text-white font-bold shadow-md">
                {profile.name ? profile.name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div>
                <h4 className="font-bold text-white text-base flex items-center gap-2">
                  {profile.name}
                  {isActive && <CheckCircle2 className="w-4 h-4 text-[#4F8BFF]" />}
                </h4>
                <span className="text-xs font-mono text-slate-400">ID: {profile.id.slice(0, 8)}...</span>
              </div>
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowDeleteModal(true);
              }}
              className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-full transition-colors"
              title="Delete Profile"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>

          {/* Stats Badges */}
          <div className="space-y-2 mb-6">
            <div className="flex items-center justify-between text-xs text-slate-400 bg-white/5 px-3 py-2 rounded-xl">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-[#4F8BFF]" /> Created
              </span>
              <span className="font-medium text-slate-200">{formatDate(profile.created_at)}</span>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 bg-white/5 px-3 py-2 rounded-xl">
              <span className="flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-[#8B5CF6]" /> Conversations
              </span>
              <span className="font-medium text-slate-200">{profile.conversation_count || 0}</span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-2">
          {isActive ? (
            <div className="w-full py-2 text-center text-xs font-semibold text-[#4F8BFF] bg-[#4F8BFF]/10 rounded-full border border-[#4F8BFF]/30">
              Active Digital Twin
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              className="w-full justify-between"
              onClick={() => onSelect(profile)}
            >
              <span>Select Twin</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </Card>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Personality Profile"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Are you sure you want to delete <strong className="text-white">{profile.name}</strong>? This action will permanently remove the personality prompt and chat history.
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
