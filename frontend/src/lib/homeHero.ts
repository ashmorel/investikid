import type { ModuleOut, LevelOut, LessonSummary } from '@/api/content';
import type { CategorisedRecommendations } from '@/api/ai';

export type HeroMode = 'start' | 'continue' | 'caught_up';

export interface TargetModule {
  moduleId: string;
  mode: 'start' | 'continue';
}

export function pickTargetModule(
  recs: CategorisedRecommendations | null | undefined,
  modules: ModuleOut[],
): TargetModule | null {
  const cont = recs?.continue_learning?.[0];
  if (cont) return { moduleId: cont.module_id, mode: 'continue' };
  const fresh = recs?.something_new?.[0];
  if (fresh) return { moduleId: fresh.module_id, mode: 'start' };
  const unlocked = modules.filter((m) => !m.locked).sort((a, b) => a.order_index - b.order_index);
  return unlocked.length > 0 ? { moduleId: unlocked[0].id, mode: 'start' } : null;
}

export function pickTargetLevel(levels: LevelOut[]): LevelOut | null {
  return [...levels]
    .sort((a, b) => a.order_index - b.order_index)
    .find((l) => l.state !== 'locked' && l.lessons_completed < l.lessons_total) ?? null;
}

export function pickTargetLesson(lessons: LessonSummary[]): LessonSummary | null {
  return [...lessons].sort((a, b) => a.order_index - b.order_index).find((l) => !l.completed) ?? null;
}

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
    return `Amazing work, ${name}! You've finished everything for now. 🎉 New quests coming soon!`;
  }
  if (ctx.mode === 'continue') {
    const streak = ctx.streakCount > 1 ? ` ${ctx.streakCount}-day streak — keep it going!` : '';
    return `Welcome back, ${name}!${streak} Let's pick up ${ctx.lessonLabel ?? 'your next quest'}.`;
  }
  return `Let's start your money journey, ${name}! First up: ${ctx.lessonLabel ?? 'your first lesson'} 📈`;
}
