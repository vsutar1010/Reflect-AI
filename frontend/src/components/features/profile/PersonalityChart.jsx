import React from 'react';

// The Big Five traits this chart knows how to display, plus every key
// alias a small local LLM's JSON has been observed to use for each one
// (e.g. "openness_to_experience" instead of "openness"). Order here is
// the display order.
const TRAITS = [
  { key: 'openness', label: 'Openness', aliases: ['openness', 'openness_to_experience', 'open'] },
  { key: 'conscientiousness', label: 'Conscientiousness', aliases: ['conscientiousness', 'conscientious'] },
  { key: 'extraversion', label: 'Extraversion', aliases: ['extraversion', 'extroversion', 'extraverted'] },
  { key: 'agreeableness', label: 'Agreeableness', aliases: ['agreeableness', 'agreeable'] },
  { key: 'neuroticism', label: 'Neuroticism', aliases: ['neuroticism', 'emotional_stability', 'neurotic'] },
];

/**
 * Turns whatever a trait's raw value looks like into a 0-100 integer, or
 * null if it can't be interpreted as a score at all. Handles both
 * conventions this codebase's data could plausibly use:
 *   - a 0-1 fraction (e.g. 0.8 -> 80)
 *   - an already-0-100 number (e.g. 80 -> 80, 1 is treated as the 0-1
 *     convention since "1%" is not a meaningful score to ever display)
 *   - a numeric string, optionally with a trailing "%"
 *   - an object carrying the score under score/value/percentage
 * Never throws -- unparseable input (strings like "High", missing,
 * null, NaN) just means "no score available for this trait".
 */
function normalizeScore(raw) {
  let value = raw;
  if (raw && typeof raw === 'object') {
    value = raw.score ?? raw.value ?? raw.percentage ?? raw.percent ?? null;
  }
  if (value === null || value === undefined) return null;

  if (typeof value === 'string') {
    value = value.trim().replace(/%$/, '');
  }

  const num = typeof value === 'number' ? value : parseFloat(value);
  if (!Number.isFinite(num)) return null;

  const percent = num >= 0 && num <= 1 ? num * 100 : num;
  return Math.round(Math.min(100, Math.max(0, percent)));
}

function extractDescription(raw) {
  if (raw && typeof raw === 'object' && typeof raw.description === 'string') {
    return raw.description.trim();
  }
  return '';
}

function findRawValue(personality, aliases) {
  for (const alias of aliases) {
    if (personality[alias] !== undefined) return personality[alias];
    // Case-insensitive fallback for keys like "Openness".
    const match = Object.keys(personality).find((k) => k.toLowerCase() === alias);
    if (match) return personality[match];
  }
  return undefined;
}

function usePersonalityTraits(personality) {
  return React.useMemo(() => {
    if (!personality || typeof personality !== 'object') return [];
    return TRAITS.map((trait) => {
      const raw = findRawValue(personality, trait.aliases);
      return {
        key: trait.key,
        label: trait.label,
        score: normalizeScore(raw),
        description: extractDescription(raw),
      };
    });
  }, [personality]);
}

function TraitBar({ label, score, description }) {
  const available = score !== null;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5 gap-3">
        <span className="text-sm font-medium text-slate-200">{label}</span>
        <span className="text-sm font-semibold text-white tabular-nums shrink-0">
          {available ? `${score}%` : 'N/A'}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={`${label}: ${available ? `${score} percent` : 'not available'}`}
        aria-valuenow={available ? score : undefined}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2.5 w-full rounded-full bg-white/5 overflow-hidden"
      >
        {available && (
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] transition-[width] duration-500 ease-out"
            style={{ width: `${score}%` }}
          />
        )}
      </div>
      {description && <p className="text-xs text-slate-500 mt-1">{description}</p>}
    </div>
  );
}

// Lightweight inline-SVG radar chart -- no charting library in this
// project, and five axes is simple enough that plain trig + a <polygon>
// is far less code (and weight) than pulling one in for this alone.
function RadarChart({ traits }) {
  // The viewBox is intentionally much larger than the plot itself --
  // trait names like "Conscientiousness" need real horizontal room to
  // avoid clipping at the SVG's own edge. `width`/`height` below scale
  // this whole coordinate space down to a compact on-card size, so the
  // generous internal margins don't inflate the actual rendered chart.
  const viewW = 480;
  const viewH = 340;
  const center = { x: viewW / 2, y: viewH / 2 };
  const radius = 78;
  const angleStep = (Math.PI * 2) / traits.length;
  // Start pointing straight up, then go clockwise.
  const angleFor = (i) => i * angleStep - Math.PI / 2;

  const pointFor = (i, fraction) => {
    const angle = angleFor(i);
    return {
      x: center.x + Math.cos(angle) * radius * fraction,
      y: center.y + Math.sin(angle) * radius * fraction,
    };
  };

  const dataPoints = traits.map((t, i) => pointFor(i, (t.score ?? 0) / 100));
  const polygonPoints = dataPoints.map((p) => `${p.x},${p.y}`).join(' ');
  const ringFractions = [0.25, 0.5, 0.75, 1];

  return (
    <svg
      viewBox={`0 0 ${viewW} ${viewH}`}
      width={260}
      height={Math.round((260 * viewH) / viewW)}
      className="mx-auto"
      role="img"
      aria-label={`Personality radar: ${traits.map((t) => `${t.label} ${t.score ?? 0} percent`).join(', ')}`}
    >
      {ringFractions.map((f) => (
        <polygon
          key={f}
          points={traits.map((_, i) => { const p = pointFor(i, f); return `${p.x},${p.y}`; }).join(' ')}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={1}
        />
      ))}
      {traits.map((_, i) => {
        const p = pointFor(i, 1);
        return (
          <line key={i} x1={center.x} y1={center.y} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.08)" strokeWidth={1} />
        );
      })}
      <polygon points={polygonPoints} fill="rgba(139,92,246,0.25)" stroke="#8B5CF6" strokeWidth={1.5} />
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="#4F8BFF" />
      ))}
      {traits.map((t, i) => {
        const p = pointFor(i, 1.28);
        const anchor = Math.abs(Math.cos(angleFor(i))) < 0.15 ? 'middle' : Math.cos(angleFor(i)) > 0 ? 'start' : 'end';
        return (
          <text key={t.key} x={p.x} y={p.y} textAnchor={anchor} dominantBaseline="middle" className="fill-slate-400" fontSize={13}>
            {t.label}
          </text>
        );
      })}
    </svg>
  );
}

function PersonalitySkeleton() {
  return (
    <div className="space-y-4 animate-pulse" aria-busy="true" aria-label="Loading personality insights">
      {TRAITS.map((t) => (
        <div key={t.key}>
          <div className="flex justify-between mb-1.5">
            <div className="h-3.5 w-24 rounded bg-white/10" />
            <div className="h-3.5 w-8 rounded bg-white/10" />
          </div>
          <div className="h-2.5 w-full rounded-full bg-white/5" />
        </div>
      ))}
    </div>
  );
}

export default function PersonalityChart({ personality, loading = false, showRadar = true }) {
  const traits = usePersonalityTraits(personality);
  const hasAnyScore = traits.some((t) => t.score !== null);

  if (loading) {
    return <PersonalitySkeleton />;
  }

  if (!hasAnyScore) {
    return (
      <p className="text-sm text-slate-500">
        Personality insights aren't available yet. Continue using ReflectAI to build your profile.
      </p>
    );
  }

  return (
    <div className={showRadar ? 'grid grid-cols-1 md:grid-cols-2 gap-8 items-center' : ''}>
      <div className="space-y-4">
        {traits.map((t) => (
          <TraitBar key={t.key} label={t.label} score={t.score} description={t.description} />
        ))}
      </div>
      {showRadar && (
        <div className="flex justify-center">
          <RadarChart traits={traits} />
        </div>
      )}
    </div>
  );
}
