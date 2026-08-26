import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mic, 
  Sparkles, 
  TrendingUp, 
  Cpu, 
  MessageSquare, 
  Brain, 
  UserCheck, 
  Send,
  Zap,
  ArrowRight,
  Shield,
  Layers,
  ChevronRight
} from 'lucide-react';
import Navbar from '../components/common/Navbar';
import AnimatedBackground from '../components/common/AnimatedBackground';
import { useAuth } from '../context/AuthContext';

// Image imports (resolved relative to src/assets/)
import voice1Image from '../assets/voice1.jpg';
import voice2Image from '../assets/voice2.jpg';
import img1Image from '../assets/img1.jpg';
import img2Image from '../assets/img2.jpg';
import img3Image from '../assets/img3.jpg';
import chat1Image from '../assets/chat1.jpg';
import chat2Image from '../assets/chat2.jpg';
import heroImage from '../assets/hero.png';

export default function Landing() {
  const { user } = useAuth();
  const [demoMessage, setDemoMessage] = useState('');
  const [demoChat, setDemoChat] = useState([
    { role: 'user', content: 'Hey twin! What is our stance on remote work?' },
    { role: 'assistant', content: 'Honestly, I prefer asynchronous focus blocks. Giving people flexibility always results in cleaner code and better motivation, as long as documentation stays tight. What do you think?' }
  ]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSendDemoMessage = (e) => {
    e.preventDefault();
    if (!demoMessage.trim()) return;

    const userMsg = demoMessage;
    setDemoChat(prev => [...prev, { role: 'user', content: userMsg }]);
    setDemoMessage('');
    setIsTyping(true);

    // Simulated twin reply
    setTimeout(() => {
      let replyContent = "That's exactly how we would phrase it. Let's optimize this flow.";
      if (userMsg.toLowerCase().includes('hello') || userMsg.toLowerCase().includes('hi')) {
        replyContent = "Hey there! Ready to bounce ideas off our own digital duplicate?";
      } else if (userMsg.toLowerCase().includes('coffee') || userMsg.toLowerCase().includes('drink')) {
        replyContent = "Double espresso, straight black. You know it. Keeps the compile loops fast!";
      } else if (userMsg.toLowerCase().includes('hobby') || userMsg.toLowerCase().includes('do for fun')) {
        replyContent = "Writing compilers, tweaking prompt layouts, and listening to synthwave. Pretty much our default state.";
      }
      setDemoChat(prev => [...prev, { role: 'assistant', content: replyContent }]);
      setIsTyping(false);
    }, 1800);
  };

  return (
    <div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] overflow-x-hidden font-sans select-none">
      {/* Subtle grid, matching the rest of the app */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff03_1px,transparent_1px),linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:4.5rem_4.5rem]" />
      </div>

      <AnimatedBackground />

      <Navbar />

      {/* --- HERO SECTION --- */}
      <header className="relative pt-36 pb-24 md:pt-48 md:pb-36 z-10 max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        {/* Hero Left Content */}
        <motion.div 
          className="lg:col-span-7 flex flex-col items-start text-left"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 text-xs font-semibold tracking-wider text-slate-300 uppercase shadow-[0_0_15px_rgba(139,92,246,0.15)] mb-6">
            <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6] animate-pulse" />
            <span>✨ AI Personality Clone</span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight leading-[1.1] mb-6">
            Create Your <br />
            <span className="bg-gradient-to-r from-[#4F8BFF] via-[#707cff] to-[#8B5CF6] bg-clip-text text-transparent drop-shadow-sm">
              Digital Twin
            </span> <br />
            in Minutes.
          </h1>

          {/* Description */}
          <p className="text-base md:text-lg text-slate-400 max-w-xl leading-relaxed mb-10">
            ReflectAI learns your unique communication style, vocabulary, humor, and behavior to build an interactive digital double that speaks, writes, and reasons exactly like you.
          </p>

          {/* Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
            <Link
              to={user ? '/analyze' : '/signup'}
              className="group relative flex items-center justify-center gap-2 px-8 py-4 bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] text-white font-semibold rounded-full overflow-hidden transition-all duration-300 hover:shadow-[0_0_25px_rgba(79,139,255,0.4)]"
            >
              Start Building
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <a 
              href="#demo"
              className="flex items-center justify-center gap-2 px-8 py-4 bg-[#09090B]/50 hover:bg-[#0f0f13] border border-white/10 rounded-full font-semibold text-slate-300 hover:text-white transition-all duration-300"
            >
              Live Chat Demo
            </a>
          </div>
        </motion.div>

        {/* Hero Right Media */}
        <motion.div 
          className="lg:col-span-5 relative w-full h-[350px] md:h-[450px] flex items-center justify-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          {/* Neon Glow Panels behind image */}
          <div className="absolute inset-0 bg-gradient-to-tr from-[#4F8BFF]/20 to-[#8B5CF6]/20 rounded-3xl blur-2xl opacity-70 animate-pulse pointer-events-none" />

          {/* Glassmorphic floating card containing voice visual */}
          <motion.div 
            className="relative w-full h-full bg-[#09090B]/60 border border-white/15 rounded-3xl overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] p-4 flex flex-col justify-between"
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          >
            {/* Darkened visual layer */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#050505]/80 z-10" />
            <img 
              src={voice1Image} 
              alt="Voice Interface hologram" 
              className="absolute inset-0 w-full h-full object-cover opacity-50 transition-opacity duration-300 hover:opacity-60"
            />
            
            {/* Overlay indicators */}
            <div className="relative z-20 flex justify-between items-start">
              <div className="bg-black/40 backdrop-blur-md border border-white/10 rounded-full px-3 py-1 text-xs text-[#4F8BFF] font-semibold flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-[#4F8BFF] animate-ping" />
                Live Clone Signal
              </div>
              <div className="bg-black/40 backdrop-blur-md border border-white/10 rounded-full px-3 py-1 text-xs text-[#8B5CF6] font-semibold">
                Ollama Engine
              </div>
            </div>

            <div className="relative z-20 text-left mt-auto">
              <p className="text-xs text-[#4F8BFF] uppercase tracking-wider font-semibold mb-1">Module 01: Voice</p>
              <h3 className="text-xl font-bold text-white mb-2">Neural Vocal Synthesis</h3>
              <p className="text-xs text-slate-400">Continuous capture matches your accent, tone variations, and speech pauses automatically.</p>
            </div>
          </motion.div>
        </motion.div>
      </header>

      {/* Discover Indicator */}
      <div className="w-full flex flex-col items-center justify-center gap-2 text-slate-500 pb-16 z-10 relative">
        <motion.div 
          animate={{ y: [0, 6, 0] }} 
          transition={{ duration: 1.5, repeat: Infinity }}
          className="text-xs uppercase tracking-widest text-[#4F8BFF] font-semibold flex items-center gap-1"
        >
          <span>Discover More</span>
        </motion.div>
        <span className="text-lg">↓</span>
      </div>

      {/* --- SECTION 2: HOW IT WORKS --- */}
      <section id="how-it-works" className="relative py-24 z-10 border-t border-white/5 bg-[#070709]/60 backdrop-blur-3xl">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-16"
          >
            <h2 className="text-xs uppercase tracking-widest text-[#8B5CF6] font-extrabold mb-3">Workflow</h2>
            <h3 className="text-3xl md:text-4xl font-bold">How ReflectAI Works</h3>
            <p className="text-slate-400 max-w-xl mx-auto mt-4 text-sm md:text-base">
              A continuous loop of capture, programmatic statistics extraction, and LLM-based personality encoding.
            </p>
          </motion.div>

          {/* Horizontal / Stacked Timeline Grid */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            {[
              { step: '01', title: 'Record Voice', icon: Mic, desc: 'Provide vocal samples to capture your tone, speed, and patterns.' },
              { step: '02', title: 'Analyze Behavior', icon: TrendingUp, desc: 'Linguistic analyzers extract punctuation, text patterns, and formatting.' },
              { step: '03', title: 'Generate Prompts', icon: Cpu, desc: 'Ollama generates an immutable system identity instruction.' },
              { step: '04', title: 'Clone Identity', icon: UserCheck, desc: 'A secure, sandboxed profile file maps your digital twin.' },
              { step: '05', title: 'Chat Naturally', icon: MessageSquare, desc: 'Interact with your clone using real-time dynamic context.' }
            ].map((item, idx) => (
              <motion.div 
                key={idx}
                className="relative group p-6 bg-[#09090B]/40 hover:bg-[#0f0f13]/60 border border-white/5 hover:border-[#4F8BFF]/30 rounded-2xl text-left transition-all duration-300 flex flex-col justify-between"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                whileHover={{ y: -6 }}
              >
                <div className="flex items-center justify-between mb-6">
                  <span className="text-xs font-mono text-slate-500 font-bold">{item.step}</span>
                  <div className="p-2.5 rounded-lg bg-[#4F8BFF]/10 text-[#4F8BFF] group-hover:bg-[#4F8BFF] group-hover:text-white transition-colors duration-300">
                    <item.icon className="w-5 h-5" />
                  </div>
                </div>
                <div>
                  <h4 className="font-bold text-white mb-2">{item.title}</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* --- SECTION 3: CORE FEATURES --- */}
      <section id="features" className="relative py-24 z-10">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-20"
          >
            <h2 className="text-xs uppercase tracking-widest text-[#4F8BFF] font-extrabold mb-3">Capabilities</h2>
            <h3 className="text-3xl md:text-4xl font-bold">Built for Neural Accuracy</h3>
            <p className="text-slate-400 max-w-xl mx-auto mt-4 text-sm md:text-base">
              A comprehensive stack of custom algorithms replicating your unique communication characteristics.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Card 1: Voice Cloning */}
            <motion.div 
              className="group bg-[#09090B]/60 border border-white/5 hover:border-[#4F8BFF]/30 rounded-3xl overflow-hidden shadow-xl transition-all duration-300"
              whileHover={{ y: -8 }}
            >
              <div className="h-48 overflow-hidden relative">
                <div className="absolute inset-0 bg-[#050505]/40 group-hover:bg-transparent transition-colors z-10" />
                <img src={voice2Image} alt="Voice interface" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              </div>
              <div className="p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Mic className="w-5 h-5 text-[#4F8BFF]" />
                  <h4 className="text-lg font-bold text-white">Neural Voice Clone</h4>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed"> Replicates cadence, volume shifts, and vocal accents with zero latency, making conversation feels like a natural stream. </p>
              </div>
            </motion.div>

            {/* Card 2: Personality Analysis */}
            <motion.div 
              className="group bg-[#09090B]/60 border border-white/5 hover:border-[#8B5CF6]/30 rounded-3xl overflow-hidden shadow-xl transition-all duration-300"
              whileHover={{ y: -8 }}
            >
              <div className="h-48 overflow-hidden relative">
                <div className="absolute inset-0 bg-[#050505]/40 group-hover:bg-transparent transition-colors z-10" />
                <img src={img1Image} alt="Personality analysis graph" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              </div>
              <div className="p-6">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="w-5 h-5 text-[#8B5CF6]" />
                  <h4 className="text-lg font-bold text-white">Linguistic Analysis</h4>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed"> Measures structural statistics including exclamation frequency, average sentence lengths, emoji counts, and phrase repetition. </p>
              </div>
            </motion.div>

            {/* Card 3: AI Twin */}
            <motion.div 
              className="group bg-[#09090B]/60 border border-white/5 hover:border-[#4F8BFF]/30 rounded-3xl overflow-hidden shadow-xl transition-all duration-300"
              whileHover={{ y: -8 }}
            >
              <div className="h-48 overflow-hidden relative">
                <div className="absolute inset-0 bg-[#050505]/40 group-hover:bg-transparent transition-colors z-10" />
                <img src={img3Image} alt="Hologram twin representation" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              </div>
              <div className="p-6">
                <div className="flex items-center gap-2 mb-3">
                  <UserCheck className="w-5 h-5 text-[#4F8BFF]" />
                  <h4 className="text-lg font-bold text-white">Custom System Prompts</h4>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed"> Encodes psychological traits, emotional states, preferred discussion topics, and values into modular config profiles. </p>
              </div>
            </motion.div>

            {/* Card 4: Smart Conversation */}
            <motion.div 
              className="group bg-[#09090B]/60 border border-white/5 hover:border-[#8B5CF6]/30 rounded-3xl overflow-hidden shadow-xl transition-all duration-300"
              whileHover={{ y: -8 }}
            >
              <div className="h-48 overflow-hidden relative">
                <div className="absolute inset-0 bg-[#050505]/40 group-hover:bg-transparent transition-colors z-10" />
                <img src={chat2Image} alt="Messaging platform simulation" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              </div>
              <div className="p-6">
                <div className="flex items-center gap-2 mb-3">
                  <MessageSquare className="w-5 h-5 text-[#8B5CF6]" />
                  <h4 className="text-lg font-bold text-white">Dynamic Context Window</h4>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed"> Injects your most recent messages to adapt response moods, vocabulary levels, and energy parameters in real-time. </p>
              </div>
            </motion.div>

            {/* Card 5: Adaptive Memory */}
            <motion.div 
              className="group p-8 bg-[#09090B]/60 border border-white/5 hover:border-[#4F8BFF]/30 rounded-3xl shadow-xl transition-all duration-300 flex flex-col justify-center"
              whileHover={{ y: -8 }}
            >
              <div className="p-4 w-14 h-14 rounded-2xl bg-[#4F8BFF]/10 text-[#4F8BFF] mb-6 flex items-center justify-center">
                <Brain className="w-7 h-7" />
              </div>
              <h4 className="text-lg font-bold text-white mb-3">Cognitive Memory Layer</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Stores context summaries, user preferences, and custom values securely across chat sessions without losing personality.
              </p>
            </motion.div>

            {/* Card 6: Local AI */}
            <motion.div 
              className="group p-8 bg-[#09090B]/60 border border-white/5 hover:border-[#8B5CF6]/30 rounded-3xl shadow-xl transition-all duration-300 flex flex-col justify-center"
              whileHover={{ y: -8 }}
            >
              <div className="p-4 w-14 h-14 rounded-2xl bg-[#8B5CF6]/10 text-[#8B5CF6] mb-6 flex items-center justify-center">
                <Cpu className="w-7 h-7" />
              </div>
              <h4 className="text-lg font-bold text-white mb-3">Local Ollama Engine</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Keeps your files private. Run entire analyses and chat twins directly using local open-source models like Mistral and Qwen.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* --- SECTION 4: DIGITAL TWIN VISUALIZATION --- */}
      <section className="relative py-24 z-10 bg-[#070709]/50 backdrop-blur-2xl border-t border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Visual Left Info */}
          <div className="lg:col-span-4 text-left">
            <h2 className="text-xs uppercase tracking-widest text-[#8B5CF6] font-extrabold mb-3">Telemetry</h2>
            <h3 className="text-3xl font-bold mb-6">Identity Telemetry</h3>
            <p className="text-slate-400 text-sm leading-relaxed mb-8">
              We extract multi-dimensional metrics to construct the exact prompt constraints of your digital double. Your personality parameters are completely mapped, validated, and updated continuously.
            </p>
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className="w-2.5 h-2.5 rounded-full bg-[#4F8BFF]" />
                <span className="text-xs font-semibold text-slate-300">Tone Variation Mapping</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2.5 h-2.5 rounded-full bg-[#8B5CF6]" />
                <span className="text-xs font-semibold text-slate-300">Punctuation Density Matrix</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2.5 h-2.5 rounded-full bg-white" />
                <span className="text-xs font-semibold text-slate-300">Linguistic Humor Indexes</span>
              </div>
            </div>
          </div>

          {/* Visual Right Representation (Human facing hologram with links) */}
          <div className="lg:col-span-8 relative w-full h-[400px] md:h-[500px] flex items-center justify-center">
            {/* Center Image */}
            <div className="relative w-64 h-64 md:w-80 md:h-80 rounded-full border border-white/10 flex items-center justify-center p-4">
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#4F8BFF]/10 to-[#8B5CF6]/10 blur-xl animate-pulse" />
              <img 
                src={img3Image} 
                alt="Digital twin core" 
                className="w-full h-full object-cover rounded-full border border-white/20 opacity-70 filter brightness-110" 
              />
            </div>

            {/* Connecting Labels and Lines */}
            {[
              { label: 'Voice Pitch', x: '-left-4 md:-left-8', y: 'top-10', anchor: 'left' },
              { label: 'Vocabulary Selection', x: 'left-20 md:left-24', y: '-top-4', anchor: 'top' },
              { label: 'Emotional Intelligence', x: '-right-4 md:-right-8', y: 'top-10', anchor: 'right' },
              { label: 'Punctuation Density', x: '-left-10 md:-left-16', y: 'bottom-20', anchor: 'left' },
              { label: 'Humor Index', x: '-right-10 md:-right-16', y: 'bottom-20', anchor: 'right' },
              { label: 'Discussion Focus', x: 'right-20 md:right-24', y: '-bottom-4', anchor: 'bottom' }
            ].map((node, i) => (
              <div key={i} className={`absolute ${node.x} ${node.y} z-20`}>
                <div className="bg-black/80 backdrop-blur-md border border-white/10 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-200 shadow-md flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#4F8BFF]" />
                  {node.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* --- SECTION 5: CONVERSATION DEMO --- */}
      <section id="demo" className="relative py-24 z-10">
        <div className="max-w-4xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-xs uppercase tracking-widest text-[#4F8BFF] font-extrabold mb-3">Simulation</h2>
            <h3 className="text-3xl font-bold">Talk to the Clone</h3>
            <p className="text-slate-400 max-w-lg mx-auto mt-4 text-sm">
              Type a greeting, talk about coffee, or ask about hobbies to test the twin's dynamic style replication.
            </p>
          </motion.div>

          {/* Interactive Chat Console */}
          <div className="bg-[#09090B]/60 border border-white/15 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-lg flex flex-col h-[450px]">
            {/* Header */}
            <div className="border-b border-white/10 px-6 py-4 flex items-center justify-between bg-black/40">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-[#4F8BFF] shadow-[0_0_8px_#4F8BFF]" />
                <h4 className="text-sm font-bold text-white tracking-wide">twin_session_active</h4>
              </div>
              <span className="text-xs text-slate-500 font-mono">Status: Connected</span>
            </div>

            {/* Chat Body */}
            <div className="flex-1 p-6 overflow-y-auto space-y-4 text-left">
              {demoChat.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-2xl px-5 py-3.5 text-sm ${msg.role === 'user' ? 'bg-[#4F8BFF] text-white rounded-br-none' : 'bg-white/5 border border-white/10 text-slate-200 rounded-bl-none'}`}>
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-none px-5 py-3.5 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}
            </div>

            {/* Input Footer */}
            <form onSubmit={handleSendDemoMessage} className="border-t border-white/10 p-4 bg-black/40 flex items-center gap-3">
              <input 
                type="text" 
                value={demoMessage}
                onChange={(e) => setDemoMessage(e.target.value)}
                placeholder="Ask your duplicate a question (e.g. coffee, hello, stance on remote work)..."
                className="flex-1 bg-white/5 border border-white/10 rounded-full px-5 py-3 text-sm text-white focus:outline-none focus:border-[#4F8BFF] transition-colors"
              />
              <button 
                type="submit" 
                className="p-3 bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] rounded-full text-white hover:shadow-[0_0_15px_rgba(79,139,255,0.4)] transition-all"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* --- SECTION 6: TECHNOLOGY STACKS --- */}
      <section id="technology" className="relative py-20 z-10 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-xs uppercase tracking-widest text-[#8B5CF6] font-bold mb-8">Integrated Technologies</p>
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-16 opacity-40 hover:opacity-60 transition-opacity duration-300">
            {['FastAPI', 'React', 'Ollama', 'MongoDB', 'Tailwind', 'Vapi', 'LangGraph', 'Whisper'].map((tech, idx) => (
              <span key={idx} className="text-base md:text-lg font-mono font-bold tracking-wider text-slate-400">
                {tech}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* --- FOOTER --- */}
      <footer className="relative border-t border-white/5 py-12 z-10 bg-black/80">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex flex-col items-center md:items-start gap-2 text-center md:text-left">
            <Link to="/" className="text-lg font-bold text-white">
              Reflect<span className="text-[#4F8BFF]">AI</span>
            </Link>
            <p className="text-xs text-slate-500">Neural Digital Identity & Replicas Platform © 2026</p>
          </div>

          <div className="flex items-center gap-8">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-xs text-slate-400 hover:text-white transition-colors">Github</a>
            <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="text-xs text-slate-400 hover:text-white transition-colors">LinkedIn</a>
            <a href="#docs" className="text-xs text-slate-400 hover:text-white transition-colors">Documentation</a>
            <a href="#privacy" className="text-xs text-slate-400 hover:text-white transition-colors">Privacy Policy</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
