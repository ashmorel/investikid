import type { AgeTier } from './ageTier';

// topic -> sort priority (lower = earlier). Unmapped topics fall back to order_index.
// The ONE place to retune per-tier module surfacing.
const PRIORITY: Record<AgeTier, Record<string, number>> = {
  explorer: { budgeting: 0, savings: 1, debt: 2 },
  investor: { stocks: 0, crypto: 1, risk: 2, real_estate: 3 },
};

const FALLBACK = Number.MAX_SAFE_INTEGER;

/** Stable tier-aware ordering by (topic priority, then order_index). Never mutates input. */
export function orderModulesForTier<T extends { topic: string; order_index: number }>(
  modules: T[],
  tier: AgeTier,
): T[] {
  const prio = PRIORITY[tier];
  return [...modules].sort((a, b) => {
    const pa = prio[a.topic] ?? FALLBACK;
    const pb = prio[b.topic] ?? FALLBACK;
    if (pa !== pb) return pa - pb;
    return a.order_index - b.order_index;
  });
}
