import { useChildSession } from '@/hooks/useChildSession';

export type AgeTier = 'explorer' | 'investor';
export const DEFAULT_TIER: AgeTier = 'explorer';

// Mascot/presentation knobs per tier — the single place to retune prominence.
export const tierConfig: Record<AgeTier, { pennyHeroSize: number }> = {
  explorer: { pennyHeroSize: 44 },
  investor: { pennyHeroSize: 32 },
};

/** The current child's live age tier (defaults to explorer until loaded). */
export function useAgeTier(): AgeTier {
  const { data } = useChildSession();
  return data?.age_tier ?? DEFAULT_TIER;
}
