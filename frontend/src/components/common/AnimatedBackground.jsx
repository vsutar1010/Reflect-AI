import React from 'react';
import ParticleNetwork from './ParticleNetwork';

/**
 * Shared ambient background — slow-drifting gradient glows and a subtle
 * particle network over a dot grid. Drop as the first child inside any
 * `relative` page wrapper; it positions itself behind the page's content
 * (same pattern Analyze/Profiles/ModeSelect already used, now shared
 * everywhere).
 *
 * Deliberately plain CSS animation (see index.css `drift-a`/`drift-b`),
 * not framer-motion: this mounts on nearly every page and runs forever,
 * so it's the one animation in the app where compositor-only transforms
 * (no per-frame JS, no layout/blur recalculation) actually matter for
 * overall UI responsiveness. Only two blurred layers, not three.
 *
 * ParticleNetwork is the one piece here that IS JS-driven (canvas), kept
 * as its own component/file since it has real setup logic (see that file
 * for why it renders as `position: fixed`).
 */
export default function AnimatedBackground() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      <div className="absolute inset-0 opacity-[0.05] [background-image:radial-gradient(circle,rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:36px_36px]" />

      <div className="bg-blob bg-blob-a absolute top-[-15%] left-[-10%] w-[55%] h-[55%] rounded-full bg-[#4F8BFF]/10 blur-[110px]" />
      <div className="bg-blob bg-blob-b absolute top-[10%] right-[-15%] w-[55%] h-[55%] rounded-full bg-[#8B5CF6]/10 blur-[110px]" />

      <ParticleNetwork />
    </div>
  );
}
