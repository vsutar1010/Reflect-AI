import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export default function TypingIndicator({ twinInitial = 'T' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-end gap-2.5 justify-start"
    >
      <div className="w-8 h-8 shrink-0 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(79,139,255,0.4)]">
        {twinInitial ? twinInitial.charAt(0).toUpperCase() : <Sparkles className="w-4 h-4" />}
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-[#09090B]/70 border border-white/10 flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-slate-400"
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </motion.div>
  );
}
