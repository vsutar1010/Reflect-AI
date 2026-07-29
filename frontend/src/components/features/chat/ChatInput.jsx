import React, { useRef } from 'react';
import { Send } from 'lucide-react';

export default function ChatInput({ value, onChange, onSend, disabled = false, placeholder = 'Message your twin...' }) {
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) onSend();
    }
  };

  const handleChange = (e) => {
    onChange(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }
  };

  return (
    <div className="flex items-end gap-3 p-4 border-t border-white/10 bg-[#050505]/80 backdrop-blur-xl">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="flex-1 resize-none bg-[#09090B]/60 border border-white/10 rounded-2xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-[#4F8BFF]/50 focus:shadow-[0_0_15px_rgba(79,139,255,0.15)] transition-all duration-300 disabled:opacity-50 max-h-40"
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="shrink-0 w-11 h-11 flex items-center justify-center rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] text-white shadow-[0_0_15px_rgba(79,139,255,0.3)] hover:shadow-[0_0_25px_rgba(139,92,246,0.5)] transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Send className="w-4 h-4" />
      </button>
    </div>
  );
}
