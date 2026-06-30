import { useTranslation } from 'react-i18next';
import { useNextLesson } from '@/hooks/useNextLesson';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { useRecommendations, useHomeGreeting } from '@/api/ai';
import { buildHeroGreeting } from '@/lib/homeHero';
import { tierConfig, DEFAULT_TIER, type AgeTier } from '@/lib/ageTier';
import { HeroCard } from '@/components/child/ui/HeroCard';
import { Penny } from '@/components/child/ui/Penny';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { TierChip } from '@/components/child/TierChip';
import { track } from '@/lib/analytics';
import { useEquippedCosmetics } from '@/api/cosmetics';
import { isStreakActive } from '@/lib/streak';

type DailyProgressStripProps = {
  xpToday: number;
  dailyGoalXp: number;
  streakActive: boolean;
  nextFreezeIn?: number;
};

/**
 * Slim daily-progress strip rendered directly under the hero CTA. Carries the
 * daily-goal bar, a "keeps your streak" hint, and the next-freeze countdown
 * (migrated from StatsCard — the B6 freeze-visibility feature).
 */
function DailyProgressStrip({ xpToday, dailyGoalXp, streakActive, nextFreezeIn }: DailyProgressStripProps) {
  const { t } = useTranslation('home');
  const goalPct = Math.min(100, Math.round((xpToday / dailyGoalXp) * 100));
  const goalMet = xpToday >= dailyGoalXp;
  const showFreeze = streakActive && typeof nextFreezeIn === 'number' && nextFreezeIn > 0;

  return (
    <div className="mt-3 rounded-2xl border border-brand-100 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold text-gray-700">
          {t('stats.dailyGoal', { xpToday, dailyGoalXp })}
        </span>
        <span aria-live="polite" className={goalMet ? 'text-xs font-extrabold text-success-700' : 'text-[11px] font-semibold text-muted-foreground'}>
          {goalMet ? t('stats.goalMet') : t('hero.keepsYourStreak')}
        </span>
      </div>
      <div
        className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
        role="progressbar"
        aria-valuenow={Math.min(xpToday, dailyGoalXp)}
        aria-valuemin={0}
        aria-valuemax={dailyGoalXp}
        aria-label={t('stats.dailyGoalAriaLabel')}
      >
        <div
          className={`h-full rounded-full transition-all ${goalMet ? 'bg-success-500' : 'bg-brand-500'}`}
          style={{ width: `${goalPct}%` }}
        />
      </div>
      {showFreeze && (
        <p className="mt-1.5 text-right text-[11px] font-semibold text-muted-foreground">
          {t('stats.nextFreezeIn', { count: nextFreezeIn })}
        </p>
      )}
    </div>
  );
}

export default function HomeHero() {
  const { t } = useTranslation('home');
  const next = useNextLesson();
  const { data: me } = useChildSession();
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();

  const name = me?.username ?? 'there';
  const streakCount = progress?.streak_count ?? 0;
  const dueCount = recs?.review_summary?.due_count ?? 0;
  const isPremium = me?.is_premium ?? false;
  const tier: AgeTier = me?.age_tier ?? DEFAULT_TIER;

  const xpToday = progress?.xp_today ?? 0;
  const dailyGoalXp = progress?.daily_goal_xp ?? 30;
  const streakActive = isStreakActive(progress?.last_activity_date ?? null, new Date());

  const { accessories: equippedAccessories, skin: equippedSkin } = useEquippedCosmetics();
  const templated = buildHeroGreeting({ name, mode: next.mode, lessonLabel: next.lessonLabel, streakCount, dueCount, tier });

  const aiQ = useHomeGreeting(
    { name, mode: next.mode, lesson_label: next.lessonLabel, streak_count: streakCount, due_count: dueCount },
    isPremium && !next.isLoading,
  );
  const greeting = (isPremium && aiQ.data?.greeting) ? aiQ.data.greeting : templated;

  const cfg = tierConfig[tier];

  return (
    <section aria-labelledby="home-hero-greeting" className="mb-2">
      <div className="flex items-start justify-between gap-2">
        {cfg.showPennyAvatar ? (
          <div className="flex min-w-0 flex-1 items-start gap-3" data-testid="penny-greeting">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-100 shadow" aria-hidden="true">
              <Penny size={cfg.pennyHeroSize} mood="happy" accessories={equippedAccessories} skin={equippedSkin} />
            </div>
            <div className="flex min-w-0 flex-col items-start gap-1">
              {cfg.showTierChip && <TierChip />}
              <p
                id="home-hero-greeting"
                className="animate-hero-in rounded-2xl rounded-tl-sm border border-brand-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-800 shadow-sm"
              >
                {greeting}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
            {cfg.showTierChip && <TierChip />}
            <p
              id="home-hero-greeting"
              className="animate-hero-in text-lg font-extrabold text-gray-900"
            >
              {greeting}
            </p>
          </div>
        )}

        {streakCount > 0 && (
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-brand-100 px-2.5 py-1 text-sm font-bold text-brand-700">
            <span aria-hidden="true">🔥</span>
            {t('hero.streakPill', { count: streakCount })}
          </span>
        )}
      </div>

      <div className="mt-3">
        {next.isLoading ? (
          <div className="h-16 animate-pulse rounded-3xl bg-brand-100" aria-hidden="true" />
        ) : next.mode === 'caught_up' || !next.to ? (
          cfg.heroVariant === 'flat' ? (
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white p-5 text-gray-900 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider opacity-90">{t('hero.allCaughtUp')}</p>
              <p className="mt-1 text-lg font-extrabold">{t('hero.allCaughtUpSub')}</p>
              <GradientButton
                to={dueCount > 0 ? '/progress' : '/lessons'}
                full
                className="mt-4 !bg-none bg-brand-700 text-white shadow-none hover:bg-brand-800"
              >
                {dueCount > 0 ? t('hero.reviewConcepts') : t('hero.exploreModules')}<span aria-hidden="true"> →</span>
              </GradientButton>
            </div>
          ) : (
            <div className="overflow-hidden rounded-3xl bg-brand-gradient p-5 text-white shadow-lg shadow-brand-600/30">
              <p className="text-xs font-bold uppercase tracking-wider opacity-90"><span aria-hidden="true">🎉 </span>{t('hero.allCaughtUp')}</p>
              <p className="mt-1 text-lg font-extrabold">{t('hero.allCaughtUpSub')}</p>
              <GradientButton
                to={dueCount > 0 ? '/progress' : '/lessons'}
                full
                className="mt-4 !bg-none bg-white text-brand-700 shadow-none hover:bg-brand-50"
              >
                {dueCount > 0 ? t('hero.reviewConcepts') : t('hero.exploreModules')}<span aria-hidden="true"> →</span>
              </GradientButton>
            </div>
          )
        ) : (
          <HeroCard
            onCtaClick={() => track('home_cta_tap', { surface: 'hero' })}
            eyebrow={next.mode === 'continue' ? (cfg.heroVariant === 'flat' ? t('hero.continue') : t('hero.continueLearning')) : t('hero.startHere')}
            icon={next.moduleIcon ?? '📈'}
            title={next.lessonLabel ?? t('hero.nextLesson')}
            subtitle={next.moduleTitle ?? undefined}
            cta={next.mode === 'continue' ? t('hero.continueCta') : t('hero.startLessonCta')}
            to={next.to!}
            variant={cfg.heroVariant}
          />
        )}

        {/* Slim daily-progress strip — goal bar + "keeps your streak" + next-freeze countdown */}
        {!next.isLoading && (
          <DailyProgressStrip
            xpToday={xpToday}
            dailyGoalXp={dailyGoalXp}
            streakActive={streakActive}
            nextFreezeIn={progress?.next_freeze_in}
          />
        )}
      </div>
    </section>
  );
}
