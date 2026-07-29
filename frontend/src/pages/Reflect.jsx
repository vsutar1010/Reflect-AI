import React from 'react';
import { Sparkles } from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Card from '../components/common/Card';
import AnimatedBackground from '../components/common/AnimatedBackground';

export default function Reflect() {
  return (
    <div className="relative min-h-screen bg-[#050505] text-white">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 pt-40 flex flex-col items-center justify-center text-center px-6">
        <Card className="max-w-md py-10 flex flex-col items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 text-[#8B5CF6] flex items-center justify-center">
            <Sparkles className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold mb-2">Reflect</h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Journaling prompts and self-reflection powered by your digital twin — coming soon.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
