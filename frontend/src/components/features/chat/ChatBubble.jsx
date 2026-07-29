import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export default function ChatBubble({ role, content, timestamp, twinInitial = 'T' }) {
  const isUser = role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex items-end gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <div className="w-8 h-8 shrink-0 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(79,139,255,0.4)]">
          {twinInitial ? twinInitial.charAt(0).toUpperCase() : <Sparkles className="w-4 h-4" />}
        </div>
      )}

      <div className={`max-w-[75%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words rounded-2xl ${
            isUser
              ? 'bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] text-white rounded-br-sm shadow-[0_0_15px_rgba(79,139,255,0.25)]'
              : 'bg-[#09090B]/70 backdrop-blur-xl border border-white/10 text-slate-200 rounded-bl-sm'
          }`}
        >
          {content}
        </div>
        {timestamp && (
          <span className="text-[10px] text-slate-500 mt-1 px-1">
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </motion.div>
  );
}
