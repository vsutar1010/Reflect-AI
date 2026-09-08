import { useEffect, useState } from 'react';

/**
 * Reads prefers-reduced-motion via matchMedia (not just a CSS override)
 * so JS-driven animations — the tech marquee, the particle network
 * background — can skip their motion path entirely instead of freezing
 * mid-frame.
 */
export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(query.matches);
    const handler = (e) => setReduced(e.matches);
    query.addEventListener('change', handler);
    return () => query.removeEventListener('change', handler);
  }, []);

  return reduced;
}
