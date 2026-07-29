import React from 'react';

const BAR_MULTIPLIERS = [0.4, 0.7, 1, 0.6, 0.9, 0.5, 0.8, 0.45, 0.95, 0.65, 0.55, 0.75];

export default function WaveformVisualizer({ level = 0, active = false, color = 'blue' }) {
  const colorClass = color === 'purple' ? 'bg-[#8B5CF6]' : 'bg-[#4F8BFF]';

  return (
    <div className="flex items-center justify-center gap-1 h-16">
      {BAR_MULTIPLIERS.map((mult, i) => {
        const baseHeight = active ? Math.max(0.12, level * mult) : 0.08;
        return (
          <span
            key={i}
            className={`w-1.5 rounded-full ${colorClass} transition-all duration-100 ease-out ${
              active ? 'opacity-90' : 'opacity-30'
            }`}
            style={{ height: `${Math.min(1, baseHeight) * 100}%` }}
          />
        );
      })}
    </div>
  );
}
