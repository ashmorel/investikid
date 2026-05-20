import { useCallback } from 'react';
import { useMediaQuery } from './useMediaQuery';

type Intensity = 'light' | 'medium' | 'heavy';

const DURATIONS: Record<Intensity, number> = {
  light: 10,
  medium: 25,
  heavy: 50,
};

/**
 * Returns a function that triggers haptic feedback via `navigator.vibrate()`.
 * No-ops when vibrate is unavailable or prefers-reduced-motion is active.
 */
export function useHaptic(): (intensity: Intensity) => void {
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');

  return useCallback(
    (intensity: Intensity) => {
      if (reducedMotion) return;
      if (typeof navigator === 'undefined' || typeof navigator.vibrate !== 'function') return;
      navigator.vibrate(DURATIONS[intensity]);
    },
    [reducedMotion],
  );
}
