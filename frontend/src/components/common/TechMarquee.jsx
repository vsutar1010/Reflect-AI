import React from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

function TechChip({ tech, colorIdx }) {
  const Icon = tech.icon;
  const accent = colorIdx % 2 === 0 ? '#4F8BFF' : '#8B5CF6';

  return (
    <div
      className="tech-chip group relative flex items-center gap-2.5 shrink-0 overflow-hidden px-4 py-2.5 md:px-5 md:py-3 rounded-full bg-[#09090B]/60 border border-white/10 backdrop-blur-sm text-slate-300 transition-all duration-300 ease-out hover:text-white hover:bg-[#0f0f13] hover:-translate-y-0.5"
      style={{ '--chip-accent': accent }}
    >
      <span className="chip-shine pointer-events-none absolute inset-0" aria-hidden="true" />
      {Icon && (
        <span
          className="relative flex items-center justify-center w-6 h-6 md:w-7 md:h-7 rounded-full shrink-0 transition-transform duration-300 ease-out group-hover:scale-110"
          style={{ background: `color-mix(in srgb, ${accent} 16%, transparent)` }}
        >
          <Icon className="w-3.5 h-3.5 md:w-4 md:h-4 transition-colors duration-300" style={{ color: accent }} />
        </span>
      )}
      <span className="relative text-xs md:text-sm font-semibold tracking-wide whitespace-nowrap">{tech.name}</span>
    </div>
  );
}

export default function TechMarquee({ items, direction = 'left', duration = 28 }) {
  const reducedMotion = usePrefersReducedMotion();

  if (reducedMotion) {
    return (
      <div className="flex flex-wrap items-center justify-center gap-3 md:gap-4 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-4 md:py-5">
        {items.map((tech, idx) => (
          <TechChip key={tech.name} tech={tech} colorIdx={idx} />
        ))}
      </div>
    );
  }

  const doubled = [...items, ...items];

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/5 bg-white/[0.02] py-3 md:py-4 [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)] [-webkit-mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
      <div
        className={`tech-marquee-track flex w-max gap-3 md:gap-4 px-3 ${direction === 'right' ? 'marquee-reverse' : ''}`}
        style={{ animationDuration: `${duration}s` }}
      >
        {doubled.map((tech, idx) => (
          <TechChip key={`${tech.name}-${idx}`} tech={tech} colorIdx={idx} />
        ))}
      </div>
    </div>
  );
}
