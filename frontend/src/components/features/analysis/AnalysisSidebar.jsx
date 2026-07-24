import React from 'react';
import { Check, Circle, HelpCircle, ShieldCheck } from 'lucide-react';
import Card from '../../common/Card';

export default function AnalysisSidebar({ currentStep = 0, totalSteps = 10, answersCount = 0 }) {
  return (
    <Card className="space-y-6">
      <div className="flex items-center gap-2 pb-4 border-b border-white/10">
        <HelpCircle className="w-5 h-5 text-[#4F8BFF]" />
        <h4 className="font-bold text-white text-base">Analysis Checklist</h4>
      </div>

      {/* Step Indicators */}
      <div className="space-y-3">
        {Array.from({ length: totalSteps }).map((_, idx) => {
          const isDone = idx < currentStep;
          const isCurrent = idx === currentStep;

          return (
            <div
              key={idx}
              className={`flex items-center gap-3 p-2.5 rounded-xl border transition-all duration-300 ${
                isCurrent
                  ? 'bg-[#4F8BFF]/10 border-[#4F8BFF]/40 text-white shadow-[0_0_10px_rgba(79,139,255,0.1)]'
                  : isDone
                  ? 'bg-white/5 border-white/10 text-slate-300'
                  : 'bg-transparent border-transparent text-slate-600'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                  isDone
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : isCurrent
                    ? 'bg-[#4F8BFF] text-white shadow-md'
                    : 'bg-white/5 text-slate-500'
                }`}
              >
                {isDone ? <Check className="w-3.5 h-3.5" /> : idx + 1}
              </div>
              <span className="text-xs font-medium">
                {isCurrent ? 'Current Question' : isDone ? 'Answer Recorded' : `Question ${idx + 1}`}
              </span>
            </div>
          );
        })}
      </div>

      {/* Tip Card */}
      <div className="bg-white/5 p-4 rounded-2xl border border-white/10 text-xs text-slate-400 space-y-2">
        <div className="flex items-center gap-1.5 font-semibold text-slate-200">
          <ShieldCheck className="w-4 h-4 text-[#8B5CF6]" />
          <span>Local & Private</span>
        </div>
        <p className="leading-relaxed">
          Your responses are processed locally by Ollama to extract linguistic statistics. No personal data leaves your machine.
        </p>
      </div>
    </Card>
  );
}
