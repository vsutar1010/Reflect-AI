import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Loader({ text = 'Loading...', fullPage = false }) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="relative">
        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] opacity-20 animate-ping absolute inset-0" />
        <Loader2 className="w-10 h-10 text-[#4F8BFF] animate-spin relative z-10" />
      </div>
      {text && <p className="text-sm font-medium text-slate-400 animate-pulse">{text}</p>}
    </div>
  );

  if (fullPage) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#050505]/80 backdrop-blur-md">
        {content}
      </div>
    );
  }

  return content;
}
