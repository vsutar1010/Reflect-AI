// Shared mood -> badge color mapping for the Reflect feature (entry list
// cards and the detail modal both need the exact same colors).
export const MOOD_STYLES = {
  Positive: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  Negative: 'text-red-400 bg-red-500/10 border-red-500/30',
  Neutral: 'text-slate-400 bg-white/5 border-white/15',
  Mixed: 'text-[#8B5CF6] bg-[#8B5CF6]/10 border-[#8B5CF6]/30',
};

export function moodBadgeClass(mood) {
  return MOOD_STYLES[mood] || MOOD_STYLES.Neutral;
}

export function formatEntryDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const isSameDay = (a, b) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);

  if (isSameDay(date, now)) return 'Today';
  if (isSameDay(date, yesterday)) return 'Yesterday';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
