import React, { useEffect, useRef } from 'react';
import { AnimatePresence } from 'framer-motion';
import ChatBubble from './ChatBubble';
import TypingIndicator from './TypingIndicator';

export default function MessageList({ messages, isTyping, twinInitial = 'T' }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const visibleMessages = messages.filter((m) => m.role !== 'system');

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scroll-smooth">
      <AnimatePresence initial={false}>
        {visibleMessages.map((m, i) => (
          <ChatBubble
            key={i}
            role={m.role}
            content={m.content}
            timestamp={m.timestamp}
            twinInitial={twinInitial}
          />
        ))}
        {isTyping && <TypingIndicator key="typing" twinInitial={twinInitial} />}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  );
}
