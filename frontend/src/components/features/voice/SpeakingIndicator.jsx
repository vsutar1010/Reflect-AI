import React from 'react';
import { motion } from 'framer-motion';
import { Mic, Sparkles } from 'lucide-react';

export default function SpeakingIndicator({ twinName, isAssistantSpeaking, isListening, connected }) {
  return (
    <div className="relative flex items-center justify-center w-40 h-40 mx-auto">
      {connected && (
        <>
          <motion.span
            className="absolute inset-0 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] opacity-20"
            animate={isAssistantSpeaking ? { scale: [1, 1.25, 1] } : { scale: 1 }}
            transition={{ duration: 1.2, repeat: isAssistantSpeaking ? Infinity : 0, ease: 'easeInOut' }}
          />
          <motion.span
            className="absolute inset-4 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] opacity-20"
            animate={isAssistantSpeaking ? { scale: [1, 1.15, 1] } : { scale: 1 }}
            transition={{ duration: 1.2, repeat: isAssistantSpeaking ? Infinity : 0, ease: 'easeInOut', delay: 0.15 }}
          />
        </>
      )}

      <div className="relative w-28 h-28 rounded-full bg-gradient-to-tr from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center text-3xl font-bold text-white shadow-[0_0_30px_rgba(79,139,255,0.35)]">
        {twinName ? twinName.charAt(0).toUpperCase() : <Sparkles className="w-10 h-10" />}
      </div>

      {connected && isListening && !isAssistantSpeaking && (
        <div className="absolute -bottom-1 -right-1 w-9 h-9 rounded-full bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center">
          <Mic className="w-4 h-4 text-emerald-400" />
        </div>
      )}
    </div>
  );
}
