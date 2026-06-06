import { isStreakActive } from '@/lib/streak';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  level: number;
  streakCount: number;
  streakFreezes: number;
  lastActivityDate: string | null;
  today?: Date;
};

export function StatsBar({ xp, level, streakCount, streakFreezes, lastActivityDate, today }: Props) {
  const now = today ?? new Date();
  const active = isStreakActive(lastActivityDate, now);
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Your progress">
      <span className="rounded-full bg-brand-gradient px-4 py-1.5 text-sm font-bold text-white">
        ⭐ Level {level}
      </span>
      <span className="rounded-full bg-brand-100 px-4 py-1.5 text-sm font-bold text-brand-800">
        {xp} XP
      </span>
      <span
        className={cn(
          'rounded-full bg-accent-100 px-4 py-1.5 text-sm font-bold text-accent-700',
          active && 'animate-pulse',
          !active && 'opacity-50',
        )}
        aria-label={active ? 'streak active' : 'streak inactive'}
      >
        🔥 {streakCount}-day streak
      </span>
      {streakFreezes > 0 && (
        <span
          role="img"
          className="rounded-full bg-brand-100 px-4 py-1.5 text-sm font-bold text-brand-800"
          aria-label={`${streakFreezes} streak freeze${streakFreezes === 1 ? '' : 's'} — saves your streak if you miss a day`}
        >
          <span aria-hidden="true">🛡️ ×{streakFreezes}</span>
        </span>
      )}
    </div>
  );
}
