import { useChildSession } from '@/hooks/useChildSession';

export type AgeTier = 'explorer' | 'investor';
export const DEFAULT_TIER: AgeTier = 'explorer';

export type TierDensity = 'cozy' | 'compact';
export type TierCelebration = 'big' | 'subtle';
export type HeroVariant = 'playful' | 'flat';

// Presentation knobs per tier — the single place to retune tone, density and prominence.
export const tierConfig: Record<
  AgeTier,
  {
    pennyHeroSize: number;
    density: TierDensity;
    celebration: TierCelebration;
    showTierChip: boolean;
    heroVariant: HeroVariant;
    showPennyAvatar: boolean;
    chipEmoji: boolean;
  }
> = {
  explorer: { pennyHeroSize: 44, density: 'cozy', celebration: 'big', showTierChip: false, heroVariant: 'playful', showPennyAvatar: true, chipEmoji: true },
  investor: { pennyHeroSize: 32, density: 'compact', celebration: 'subtle', showTierChip: true, heroVariant: 'flat', showPennyAvatar: false, chipEmoji: false },
};

// Card-grid gap per density (full class literals so Tailwind keeps them).
export const densityGridGap: Record<TierDensity, string> = {
  cozy: 'gap-3',
  compact: 'gap-2',
};

/** The current child's live age tier (defaults to explorer until loaded). */
export function useAgeTier(): AgeTier {
  const { data } = useChildSession();
  return data?.age_tier ?? DEFAULT_TIER;
}
