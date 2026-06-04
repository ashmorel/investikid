import { cn } from '@/lib/utils';

export function LevelProgressCard({
  level,
  xp,
  className,
}: {
  level: number;
  xp: number;
  className?: string;
}) {
  const xpForNext = 100;
  const xpInLevel = xp % xpForNext;
  const pct = Math.min(100, Math.round((xpInLevel / xpForNext) * 100));
  const toGo = xpForNext - xpInLevel;
  return (
    <div className={cn('rounded-2xl border border-brand-100 bg-card p-4 shadow-sm', className)}>
      <div className="flex items-center gap-3">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-white shadow"
          aria-hidden="true"
        >
          <span className="text-sm font-extrabold">L{level}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between">
            <span className="text-sm font-extrabold text-ink">Level {level} Investor</span>
            <span className="text-xs font-bold text-brand-600">{xpInLevel} / {xpForNext} XP</span>
          </div>
          <div
            className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
            role="progressbar"
            aria-valuenow={xpInLevel}
            aria-valuemin={0}
            aria-valuemax={xpForNext}
            aria-label={`Level ${level} progress`}
          >
            <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
      <p className="mt-2 text-right text-[11px] font-semibold text-muted-foreground">
        {toGo} XP to level {level + 1}
      </p>
    </div>
  );
}
