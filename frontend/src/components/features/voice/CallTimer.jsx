import React from 'react';
import { Clock } from 'lucide-react';

function formatDuration(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export default function CallTimer({ seconds, active }) {
  return (
    <div className="inline-flex items-center gap-1.5 text-sm font-mono text-slate-300">
      <Clock className={`w-3.5 h-3.5 ${active ? 'text-[#4F8BFF]' : 'text-slate-500'}`} />
      {formatDuration(seconds)}
    </div>
  );
}
