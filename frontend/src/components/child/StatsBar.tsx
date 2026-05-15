import { isStreakActive } from '@/lib/streak';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  level: number;
  streakCount: number;
  lastActivityDate: string | null;
  today?: Date;
};

export function StatsBar({ xp, level, streakCount, lastActivityDate, today }: Props) {
  const now = today ?? new Date();
  const active = isStreakActive(lastActivityDate, now);
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Your progress">
      <span className="rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-1.5 text-sm font-bold text-white">
        ⭐ Level {level}
      </span>
      <span className="rounded-full bg-blue-100 px-4 py-1.5 text-sm font-bold text-blue-800">
        {xp} XP
      </span>
      <span
        className={cn(
          'rounded-full bg-amber-100 px-4 py-1.5 text-sm font-bold text-amber-800',
          active && 'animate-pulse',
          !active && 'opacity-50',
        )}
        aria-label={active ? 'streak active' : 'streak inactive'}
      >
        🔥 {streakCount}-day streak
      </span>
    </div>
  );
}
