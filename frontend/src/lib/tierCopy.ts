import type { AgeTier } from './ageTier';
import type { HeroGreetingCtx } from './homeHero';

/** Per-tier hero greeting builders. Explorer = warm + light emoji; investor = cool, no emoji. */
export const HERO_GREETING: Record<AgeTier, (ctx: HeroGreetingCtx) => string> = {
  explorer: (ctx) => {
    const name = ctx.name || 'there';
    if (ctx.dueCount > 0) {
      const plural = ctx.dueCount === 1 ? 'concept' : 'concepts';
      return `Welcome back, ${name}! You've got ${ctx.dueCount} ${plural} ready to review. 🧠`;
    }
    if (ctx.mode === 'caught_up') {
      return `Amazing work, ${name}! You've finished everything for now. 🎉 New lessons coming soon!`;
    }
    if (ctx.mode === 'continue') {
      const streak = ctx.streakCount > 1 ? ` ${ctx.streakCount}-day streak — keep it going!` : '';
      return `Welcome back, ${name}!${streak} Let's pick up ${ctx.lessonLabel ?? 'your next lesson'}.`;
    }
    return `Let's start your money journey, ${name}! First up: ${ctx.lessonLabel ?? 'your first lesson'} 📈`;
  },
  investor: (ctx) => {
    const name = ctx.name || 'there';
    if (ctx.dueCount > 0) {
      const plural = ctx.dueCount === 1 ? 'concept' : 'concepts';
      return `Welcome back, ${name}. You have ${ctx.dueCount} ${plural} to review.`;
    }
    if (ctx.mode === 'caught_up') {
      return `Nice work, ${name}. You're all caught up — more lessons coming soon.`;
    }
    if (ctx.mode === 'continue') {
      const streak = ctx.streakCount > 1 ? ` ${ctx.streakCount}-day streak.` : '';
      return `Welcome back, ${name}.${streak} Pick up where you left off: ${ctx.lessonLabel ?? 'your next lesson'}.`;
    }
    return `Let's get started, ${name}. First up: ${ctx.lessonLabel ?? 'your first lesson'}.`;
  },
};

/** Per-tier rotating encouragement lines for the lesson header. */
export const ENCOURAGEMENT: Record<AgeTier, string[]> = {
  explorer: [
    "Let's learn something new!",
    "You're doing great!",
    "Let's go, investor!",
  ],
  investor: [
    'Solid progress.',
    'Keep going.',
    'Good reasoning.',
    'On track.',
  ],
};
