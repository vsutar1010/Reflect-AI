import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function VoiceTranscript({ transcript, twinInitial = 'T' }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  if (transcript.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
        Live transcript will appear here once the call connects.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
      <AnimatePresence initial={false}>
        {transcript.map((entry, i) => {
          const isUser = entry.role === 'user';
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: entry.final ? 1 : 0.6, y: 0 }}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-3.5 py-2 rounded-2xl text-sm leading-relaxed ${
                  isUser
                    ? 'bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] text-white rounded-br-sm'
                    : 'bg-[#09090B]/70 border border-white/10 text-slate-200 rounded-bl-sm'
                } ${!entry.final ? 'italic' : ''}`}
              >
                {!isUser && (
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[#4F8BFF] block mb-0.5">
                    {twinInitial}
                  </span>
                )}
                {typeof entry.text === 'string' ? entry.text : ''}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  );
}
