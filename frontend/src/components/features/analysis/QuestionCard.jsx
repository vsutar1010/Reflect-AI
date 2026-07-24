import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, MessageSquare } from 'lucide-react';
import Button from '../../common/Button';
import Card from '../../common/Card';

export default function QuestionCard({ question, onSubmit, loading, questionIndex }) {
  const [answer, setAnswer] = useState('');

  // Reset answer when question updates
  useEffect(() => {
    setAnswer('');
  }, [questionIndex]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!answer.trim() || loading) return;
    onSubmit(answer.trim());
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit();
    }
  };

  return (
    <Card className="flex flex-col space-y-6">
      {/* Question Header */}
      <div className="flex items-start gap-4 pb-4 border-b border-white/10">
        <div className="p-3 rounded-2xl bg-gradient-to-tr from-[#4F8BFF]/20 to-[#8B5CF6]/20 border border-white/10 text-[#4F8BFF] mt-1 shrink-0">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <span className="text-xs font-semibold text-[#8B5CF6] uppercase tracking-wider block mb-1">
            Question #{questionIndex + 1}
          </span>
          <h3 className="text-lg md:text-xl font-bold text-white leading-relaxed">
            {question || 'Initializing interview question...'}
          </h3>
        </div>
      </div>

      {/* Answer Input */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your natural response here... Speak freely as you would in conversation. (Ctrl+Enter to submit)"
            rows={4}
            disabled={loading}
            className="w-full bg-white/5 border border-white/10 focus:border-[#4F8BFF] rounded-2xl p-4 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-[#4F8BFF]/30 transition-all duration-200 resize-none disabled:opacity-50"
          />
          <div className="absolute right-3 bottom-3 text-[11px] text-slate-500 font-mono">
            {answer.length} chars
          </div>
        </div>

        {/* Action Row */}
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-slate-500 hidden sm:inline">
            Press <kbd className="px-1.5 py-0.5 bg-white/10 rounded text-[10px] text-slate-300 font-mono">Ctrl + Enter</kbd> to submit
          </span>
          <Button
            type="submit"
            variant="primary"
            size="md"
            loading={loading}
            disabled={!answer.trim()}
            icon={Send}
            className="ml-auto"
          >
            Submit Response
          </Button>
        </div>
      </form>
    </Card>
  );
}
