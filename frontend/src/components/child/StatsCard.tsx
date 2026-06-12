import { isStreakActive } from '@/lib/streak';
import { tierConfig, useAgeTier } from '@/lib/ageTier';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  level: number;
  streakCount: number;
  streakFreezes: number;
  lastActivityDate: string | null;
  today?: Date;
};

const XP_FOR_NEXT = 100;

export function StatsCard({ xp, level, streakCount, streakFreezes, lastActivityDate, today }: Props) {
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;
  const active = isStreakActive(lastActivityDate, today ?? new Date());
  const xpInLevel = xp % XP_FOR_NEXT;
  const pct = Math.min(100, Math.round((xpInLevel / XP_FOR_NEXT) * 100));
  const toGo = XP_FOR_NEXT - xpInLevel;

  return (
    <div className="rounded-2xl border border-brand-200 bg-card p-4 shadow-sm" role="group" aria-label="Your progress">
      <div className="flex items-center justify-between gap-2">
        {/* Level chip */}
        <span className="text-sm font-extrabold text-ink">
          {emoji && <span aria-hidden="true">⭐ </span>}Level {level}
        </span>

        {/* Streak + freeze cluster */}
        <span className={cn('flex items-center gap-1.5 text-sm font-bold text-gray-700', !active && 'opacity-50')}>
          {emoji && <span aria-hidden="true">🔥</span>}
          <span aria-label={active ? 'streak active' : 'streak inactive'}>
            {streakCount}-day streak
          </span>
          {streakFreezes > 0 && (
            <span
              role="img"
              aria-label={`${streakFreezes} streak freeze${streakFreezes === 1 ? '' : 's'} — saves your streak if you miss a day`}
            >
              {emoji
                ? <span aria-hidden="true">· 🛡️ ×{streakFreezes}</span>
                : `· ${streakFreezes} freeze${streakFreezes === 1 ? '' : 's'}`}
            </span>
          )}
        </span>
      </div>

      {/* XP progress bar */}
      <div
        className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
        role="progressbar"
        aria-valuenow={xpInLevel}
        aria-valuemin={0}
        aria-valuemax={XP_FOR_NEXT}
        aria-label={`Level ${level} progress`}
      >
        <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${pct}%` }} />
      </div>

      <p className="mt-1.5 text-right text-[11px] font-semibold text-muted-foreground">
        {xpInLevel} / {XP_FOR_NEXT} XP · {toGo} XP to Level {level + 1}
      </p>
    </div>
  );
}
