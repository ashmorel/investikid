import { Flame, Star, TrendingUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { isStreakActive } from '@/lib/streak';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  streakCount: number;
  lastActivityDate: string | null;
  today?: Date;
};

export function XpSummary({ xp, streakCount, lastActivityDate, today }: Props) {
  const { t } = useTranslation('child');
  const now = today ?? new Date();
  const level = Math.floor(xp / 100) + 1;
  const progress = xp % 100;
  const active = isStreakActive(lastActivityDate, now);

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="grid gap-6 sm:grid-cols-3">
        {/* Level + progress bar */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <TrendingUp className="h-4 w-4" />
            {t('xpSummary.levelLabel')}
          </div>
          <p className="text-2xl font-bold">{t('xpSummary.level', { level })}</p>
          <div
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t('xpSummary.xpAriaLabel')}
            className="h-2 w-full rounded-full bg-muted"
          >
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground">{t('xpSummary.xpProgress', { progress })}</p>
        </div>

        {/* Total XP */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Star className="h-4 w-4" />
            {t('xpSummary.totalXpLabel')}
          </div>
          <p className="text-2xl font-bold">{xp}</p>
        </div>

        {/* Streak */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Flame className="h-4 w-4" />
            {t('xpSummary.streakLabel')}
          </div>
          <p
            className={cn('text-2xl font-bold', !active && 'opacity-50')}
            aria-label={active ? t('xpSummary.streakActiveAria') : t('xpSummary.streakInactiveAria')}
          >
            {t('xpSummary.streakDays', { count: streakCount })}
          </p>
          <p className="text-xs text-muted-foreground">
            {active ? t('xpSummary.streakActiveText') : t('xpSummary.streakInactiveText')}
          </p>
        </div>
      </div>
    </div>
  );
}
