export type HeroMode = 'start' | 'continue' | 'caught_up';

export interface HeroGreetingCtx {
  name: string;
  mode: HeroMode;
  lessonLabel: string | null;
  streakCount: number;
  dueCount: number;
}

export function buildHeroGreeting(ctx: HeroGreetingCtx): string {
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
}
