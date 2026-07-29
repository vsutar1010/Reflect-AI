import React from 'react';
import { motion } from 'framer-motion';

/**
 * Shared ambient background — slow-drifting gradient glows over a subtle
 * dot grid. Drop as the first child inside any `relative` page wrapper;
 * it positions itself absolutely behind the page's content (same pattern
 * Analyze/Profiles/ModeSelect already used, now shared everywhere).
 */
export default function AnimatedBackground() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      <div className="absolute inset-0 opacity-[0.05] [background-image:radial-gradient(circle,rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:36px_36px]" />

      <motion.div
        className="absolute top-[-15%] left-[-10%] w-[55%] h-[55%] rounded-full bg-[#4F8BFF]/10 blur-[150px]"
        animate={{ x: [0, 40, -15, 0], y: [0, 25, -15, 0], scale: [1, 1.08, 0.95, 1] }}
        transition={{ duration: 24, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute top-[10%] right-[-15%] w-[55%] h-[55%] rounded-full bg-[#8B5CF6]/10 blur-[150px]"
        animate={{ x: [0, -30, 20, 0], y: [0, -20, 15, 0], scale: [1, 0.95, 1.06, 1] }}
        transition={{ duration: 28, repeat: Infinity, ease: 'easeInOut', delay: 1.5 }}
      />
      <motion.div
        className="absolute bottom-[-15%] left-[20%] w-[45%] h-[45%] rounded-full bg-[#4F8BFF]/5 blur-[150px]"
        animate={{ x: [0, 25, -15, 0], y: [0, -15, 10, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
      />
    </div>
  );
}
