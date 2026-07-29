import React from 'react';
import { Loader2, PhoneOff, Radio, AlertCircle } from 'lucide-react';

const STATUS_MAP = {
  idle: { label: 'Not Connected', color: 'text-slate-400', bg: 'bg-white/5 border-white/10', icon: Radio },
  connecting: { label: 'Connecting...', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30', icon: Loader2 },
  connected: { label: 'Live', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30', icon: Radio },
  ended: { label: 'Call Ended', color: 'text-slate-400', bg: 'bg-white/5 border-white/10', icon: PhoneOff },
  error: { label: 'Connection Error', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', icon: AlertCircle },
};

export default function ConnectionStatus({ status }) {
  const config = STATUS_MAP[status] || STATUS_MAP.idle;
  const Icon = config.icon;
  const isSpinning = status === 'connecting';
  const isPulsing = status === 'connected';

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold uppercase tracking-wider ${config.bg} ${config.color}`}>
      <span className="relative flex items-center justify-center w-3 h-3">
        {isPulsing && <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />}
        <Icon className={`w-3 h-3 relative ${isSpinning ? 'animate-spin' : ''}`} />
      </span>
      {config.label}
    </div>
  );
}
