import React from 'react';
import { motion } from 'framer-motion';

export default function ProgressCard({ progress = 0, currentQuestion = 1, totalQuestions = 10 }) {
  return (
    <div className="w-full bg-[#09090B]/60 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-lg">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2">
        <span className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#4F8BFF] animate-pulse" />
          Question {currentQuestion} of {totalQuestions}
        </span>
        <span className="font-mono text-[#4F8BFF]">{Math.round(progress)}% Complete</span>
      </div>

      {/* Progress Bar Container */}
      <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden p-0.5 border border-white/5">
        <motion.div
          className="h-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] rounded-full shadow-[0_0_10px_#4F8BFF]"
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}
