import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';

const GithubIcon = ({ className }) => (
  <svg 
    viewBox="0 0 24 24" 
    stroke="currentColor" 
    strokeWidth="2" 
    fill="none" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    className={className}
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-6 left-1/2 -translate-x-1/2 w-[90%] max-w-6xl z-50 bg-[#09090B]/40 backdrop-blur-xl border border-white/10 rounded-full px-6 py-3 transition-all duration-300">
      <div className="flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] shadow-[0_0_10px_#4F8BFF]" />
          Reflect<span className="text-[#4F8BFF]">AI</span>
        </Link>

        {/* Center Links */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm text-slate-400 hover:text-white transition-colors">Features</a>
          <a href="#how-it-works" className="text-sm text-slate-400 hover:text-white transition-colors">How it Works</a>
          <a href="#technology" className="text-sm text-slate-400 hover:text-white transition-colors">Technology</a>
          <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors">Pricing</a>
          <a 
            href="https://github.com" 
            target="_blank" 
            rel="noopener noreferrer" 
            className="text-sm text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors"
          >
            <GithubIcon className="w-4 h-4" /> Github
          </a>
        </div>

        {/* Right CTA */}
        <div className="hidden md:flex items-center gap-4">
          <Link to="/profiles" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
            Profiles
          </Link>
          <Link 
            to="/analyze" 
            className="text-sm font-semibold bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] hover:from-[#3b7aff] hover:to-[#7c4bf2] text-white px-5 py-2 rounded-full transition-all duration-300 shadow-[0_0_15px_rgba(79,139,255,0.3)] hover:shadow-[0_0_20px_rgba(139,92,246,0.5)]"
          >
            Get Started
          </Link>
        </div>

        {/* Mobile menu button */}
        <button className="md:hidden text-white" onClick={() => setIsOpen(!isOpen)}>
          {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden mt-4 flex flex-col gap-4 pb-4 px-2 border-t border-white/5 pt-4">
          <a href="#features" className="text-sm text-slate-400 hover:text-white transition-colors" onClick={() => setIsOpen(false)}>Features</a>
          <a href="#how-it-works" className="text-sm text-slate-400 hover:text-white transition-colors" onClick={() => setIsOpen(false)}>How it Works</a>
          <a href="#technology" className="text-sm text-slate-400 hover:text-white transition-colors" onClick={() => setIsOpen(false)}>Technology</a>
          <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors" onClick={() => setIsOpen(false)}>Pricing</a>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-sm text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors">
            <GithubIcon className="w-4 h-4" /> Github
          </a>
          <div className="flex flex-col gap-2 pt-2 border-t border-white/5">
            <Link to="/profiles" className="text-sm text-center font-medium text-slate-300 hover:text-white py-2 transition-colors" onClick={() => setIsOpen(false)}>
              Profiles
            </Link>
            <Link 
              to="/analyze" 
              className="text-sm text-center font-semibold bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] text-white py-2.5 rounded-full transition-all duration-300"
              onClick={() => setIsOpen(false)}
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
