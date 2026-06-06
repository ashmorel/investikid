import { type AgeTier, DEFAULT_TIER } from './ageTier';
import { HERO_GREETING } from './tierCopy';

export type HeroMode = 'start' | 'continue' | 'caught_up';

export interface HeroGreetingCtx {
  name: string;
  mode: HeroMode;
  lessonLabel: string | null;
  streakCount: number;
  dueCount: number;
  tier?: AgeTier;
}

export function buildHeroGreeting(ctx: HeroGreetingCtx): string {
  return HERO_GREETING[ctx.tier ?? DEFAULT_TIER](ctx);
}
