import { useTranslation } from 'react-i18next';
import { isStreakActive } from '@/lib/streak';

type Props = {
  xp: number;
  streakCount: number;
  lastActivityDate: string | null;
  badgeCount: number;
  challengeCount: number;
  today?: Date;
};

// Personal headline for the Stats page: a brand-gradient hero with level + total
// XP, a streak pill, a level-progress bar, and at-a-glance badge/challenge chips.
// All values come from the existing progress/badges/challenges data — no new API.
export function StatsHero({ xp, streakCount, lastActivityDate, badgeCount, challengeCount, today }: Props) {
  const { t } = useTranslation('child');
  const now = today ?? new Date();
  const level = Math.floor(xp / 100) + 1;
  const progress = xp % 100;
  const active = isStreakActive(lastActivityDate, now);

  return (
    <section className="rounded-2xl bg-brand-gradient p-4 text-white sm:p-5" aria-label={t('xpSummary.levelLabel')}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-white/85">{t('xpSummary.level', { level })}</p>
          <p className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold">{xp}</span>
            <span className="text-sm font-bold text-white/85">{t('stats.xpUnit')}</span>
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full bg-white/20 px-3 py-1.5 text-sm font-bold ${active ? '' : 'opacity-60'}`}
          aria-label={active ? t('xpSummary.streakActiveAria') : t('xpSummary.streakInactiveAria')}
        >
          {t('stats.streakPill', { count: streakCount })}
        </span>
      </div>

      <div
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={t('xpSummary.xpAriaLabel')}
        className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/25"
      >
        <div className="h-full rounded-full bg-white" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-1 text-xs text-white/80">{t('stats.toNextLevel', { xp: 100 - progress })}</p>

      <div className="mt-3 flex gap-2">
        <span className="flex-1 rounded-lg bg-white/15 py-1.5 text-center text-xs font-bold">
          {t('stats.heroBadges', { count: badgeCount })}
        </span>
        <span className="flex-1 rounded-lg bg-white/15 py-1.5 text-center text-xs font-bold">
          {t('stats.heroChallenges', { count: challengeCount })}
        </span>
      </div>
    </section>
  );
}
