import { useTranslation } from 'react-i18next';
import { isStreakActive } from '@/lib/streak';
import { tierConfig, useAgeTier } from '@/lib/ageTier';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  level: number;
  streakCount: number;
  streakFreezes: number;
  lastActivityDate: string | null;
  dailyGoalXp?: number;
  xpToday?: number;
  today?: Date;
};

const XP_FOR_NEXT = 100;

export function StatsCard({ xp, level, streakCount, streakFreezes, lastActivityDate, dailyGoalXp = 30, xpToday = 0, today }: Props) {
  const { t } = useTranslation('home');
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;
  const active = isStreakActive(lastActivityDate, today ?? new Date());
  const xpInLevel = xp % XP_FOR_NEXT;
  const toGo = XP_FOR_NEXT - xpInLevel;
  const goalPct = Math.min(100, Math.round((xpToday / dailyGoalXp) * 100));
  const goalMet = xpToday >= dailyGoalXp;

  return (
    <div className="rounded-2xl border border-brand-200 bg-card p-4 shadow-sm" role="group" aria-label={t('stats.ariaLabel')}>
      <div className="flex items-center justify-between gap-2">
        {/* Level chip */}
        <span className="flex items-center gap-1 text-sm font-extrabold text-ink">
          {emoji && <span aria-hidden="true">⭐</span>}{t('stats.level', { level })}
        </span>

        {/* Right cluster: streak + freeze chip */}
        <span className="flex items-center gap-1.5">
          <span className={cn('flex items-center gap-1.5 text-sm font-bold text-gray-700', !active && 'opacity-50')}>
            {emoji && <span aria-hidden="true">🔥</span>}
            <span aria-label={active ? t('stats.streakActive') : t('stats.streakInactive')}>
              {t('stats.streak', { count: streakCount })}
            </span>
          </span>
          {streakFreezes > 0 && (
            <span
              role="img"
              className="text-sm font-bold text-gray-700"
              aria-label={streakFreezes === 1 ? t('stats.freezeAriaLabel', { count: streakFreezes }) : t('stats.freezeAriaLabelPlural', { count: streakFreezes })}
            >
              {emoji
                ? <><span aria-hidden="true">🛡</span><span aria-hidden="true"> ×</span>{streakFreezes}</>
                : (streakFreezes === 1 ? t('stats.freezeText', { count: streakFreezes }) : t('stats.freezeTextPlural', { count: streakFreezes }))}
            </span>
          )}
        </span>
      </div>

      {/* Daily goal bar — the actionable element */}
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-xs font-bold text-gray-700">
          {t('stats.dailyGoal', { xpToday, dailyGoalXp })}
        </span>
        <span aria-live="polite" className={goalMet ? 'text-xs font-extrabold text-success-700' : 'sr-only'}>
          {goalMet ? (emoji ? t('stats.goalMet') : t('stats.goalMetSimple')) : ''}
        </span>
      </div>
      <div
        className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
        role="progressbar"
        aria-valuenow={Math.min(xpToday, dailyGoalXp)}
        aria-valuemin={0}
        aria-valuemax={dailyGoalXp}
        aria-label={t('stats.dailyGoalAriaLabel')}
      >
        <div
          className={`h-full rounded-full transition-all ${goalMet ? 'bg-success-500' : 'bg-brand-gradient'}`}
          style={{ width: `${goalPct}%` }}
        />
      </div>

      <p className="mt-1.5 text-right text-[11px] font-semibold text-muted-foreground">
        {t('stats.xpProgress', { xpInLevel, xpForNext: XP_FOR_NEXT, toGo, nextLevel: level + 1 })}
      </p>
    </div>
  );
}
