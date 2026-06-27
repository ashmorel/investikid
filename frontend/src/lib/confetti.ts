/**
 * Confetti burst helper (juice pack, spec D). Callers gate on tier
 * (`tierConfig[tier].celebration === 'big'`) and reduced motion —
 * this helper just fires the burst.
 *
 * `canvas-confetti` is imported lazily so it stays out of the boot bundle — it's
 * only needed at the moment of celebration, which is rare and never on first paint.
 * This is the single import site for the lib; callers pass overrides rather than
 * importing `canvas-confetti` directly (which would pull it back into their chunk).
 */
type ConfettiOpts = { particleCount?: number; spread?: number; origin?: { x?: number; y?: number } };

export function celebrate(opts: ConfettiOpts = {}): void {
  void import('canvas-confetti').then(({ default: confetti }) => {
    confetti({ particleCount: 120, spread: 75, origin: { y: 0.6 }, ...opts });
  });
}
