import React from 'react';
import { motion } from 'framer-motion';

export default function Card({
  children,
  className = '',
  hover = false,
  glow = false,
  onClick,
  ...props
}) {
  return (
    <motion.div
      whileHover={hover ? { y: -4, transition: { duration: 0.2 } } : {}}
      onClick={onClick}
      className={`relative bg-[#09090B]/60 backdrop-blur-xl border border-white/10 rounded-2xl p-6 transition-all duration-300 ${
        glow ? 'hover:border-[#4F8BFF]/40 hover:shadow-[0_0_25px_rgba(79,139,255,0.15)]' : ''
      } ${onClick ? 'cursor-pointer' : ''} ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  );
}
