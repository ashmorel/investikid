/**
 * Confetti burst helper (juice pack, spec D). Callers gate on tier
 * (`tierConfig[tier].celebration === 'big'`) and reduced motion —
 * this helper just fires the burst.
 */
import confetti from 'canvas-confetti';

export function celebrate(): void {
  confetti({ particleCount: 120, spread: 75, origin: { y: 0.6 } });
}
