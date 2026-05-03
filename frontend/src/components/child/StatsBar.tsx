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
      <Chip>Level {level}</Chip>
      <Chip>{xp} XP</Chip>
      <Chip
        className={cn(!active && 'opacity-50')}
        aria-label={active ? 'streak active' : 'streak inactive'}
      >
        🔥 {streakCount}-day
      </Chip>
    </div>
  );
}

function Chip({ children, className, ...rest }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        'rounded-full border bg-card px-3 py-1 text-sm font-medium',
        className,
      )}
      {...rest}
    >
      {children}
    </span>
  );
}
