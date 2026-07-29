import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MessageSquare, Mic, Sparkles, Users } from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import AnimatedBackground from '../components/common/AnimatedBackground';
import { useProfile } from '../context/ProfileContext';

export default function ModeSelect() {
  const { selectedProfile } = useProfile();

  if (!selectedProfile) {
    return (
      <div className="relative min-h-screen bg-[#050505] text-white">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 pt-40 flex flex-col items-center justify-center text-center px-6">
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
            <Users className="w-7 h-7 text-slate-400" />
          </div>
          <h1 className="text-2xl font-bold mb-2">No Twin Selected</h1>
          <p className="text-slate-400 max-w-md mb-6">
            Choose or create a digital twin before starting a conversation.
          </p>
          <Link to="/profiles">
            <Button>Go to Profiles</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] font-sans">
      <AnimatedBackground />

      <Navbar />

      <main className="relative z-10 max-w-4xl mx-auto px-6 pt-36 pb-24 flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center text-2xl font-bold mb-5 shadow-[0_0_25px_rgba(79,139,255,0.3)]">
          {selectedProfile.name ? selectedProfile.name.charAt(0).toUpperCase() : 'T'}
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 text-xs font-semibold text-[#8B5CF6] uppercase mb-3">
          <Sparkles className="w-3.5 h-3.5" /> {selectedProfile.name}
        </div>

        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white text-center mb-3">
          How do you want to talk?
        </h1>
        <p className="text-slate-400 text-sm max-w-md text-center mb-12">
          Both modes are the same digital twin — same personality, same memory. Pick whichever
          feels right for this conversation.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 w-full">
          <Link to="/chat">
            <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.2 }}>
              <Card hover glow className="h-full flex flex-col items-center text-center gap-4 py-10">
                <div className="w-14 h-14 rounded-2xl bg-[#4F8BFF]/10 border border-[#4F8BFF]/20 text-[#4F8BFF] flex items-center justify-center">
                  <MessageSquare className="w-7 h-7" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white mb-1.5">Text Chat</h2>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    Type back and forth, just like messaging the real person.
                  </p>
                </div>
                <Button variant="secondary" className="mt-2">
                  Start Texting
                </Button>
              </Card>
            </motion.div>
          </Link>

          <Link to="/voice">
            <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.2 }}>
              <Card hover glow className="h-full flex flex-col items-center text-center gap-4 py-10">
                <div className="w-14 h-14 rounded-2xl bg-[#8B5CF6]/10 border border-[#8B5CF6]/20 text-[#8B5CF6] flex items-center justify-center">
                  <Mic className="w-7 h-7" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white mb-1.5">Voice Chat</h2>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    A live spoken conversation — hear the twin talk back in real time.
                  </p>
                </div>
                <Button variant="secondary" className="mt-2">
                  Start Talking
                </Button>
              </Card>
            </motion.div>
          </Link>
        </div>
      </main>
    </div>
  );
}
