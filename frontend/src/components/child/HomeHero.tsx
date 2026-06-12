import { motion } from 'framer-motion';
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

export default function HomeHero() {
  const next = useNextLesson();
  const { data: me } = useChildSession();
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();

  const name = me?.username ?? 'there';
  const streakCount = progress?.streak_count ?? 0;
  const dueCount = recs?.review_summary?.due_count ?? 0;
  const isPremium = me?.is_premium ?? false;
  const tier: AgeTier = me?.age_tier ?? DEFAULT_TIER;

  const templated = buildHeroGreeting({ name, mode: next.mode, lessonLabel: next.lessonLabel, streakCount, dueCount, tier });

  const aiQ = useHomeGreeting(
    { name, mode: next.mode, lesson_label: next.lessonLabel, streak_count: streakCount, due_count: dueCount },
    isPremium && !next.isLoading,
  );
  const greeting = (isPremium && aiQ.data?.greeting) ? aiQ.data.greeting : templated;

  const cfg = tierConfig[tier];

  return (
    <section aria-labelledby="home-hero-greeting" className="mb-2">
      {cfg.showPennyAvatar ? (
        <div className="flex items-start gap-3" data-testid="penny-greeting">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-100 shadow" aria-hidden="true">
            <Penny size={cfg.pennyHeroSize} mood="happy" />
          </div>
          <div className="flex min-w-0 flex-col items-start gap-1">
            {cfg.showTierChip && <TierChip />}
            <motion.p
              id="home-hero-greeting"
              className="rounded-2xl rounded-tl-sm border border-brand-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-800 shadow-sm"
              initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
            >
              {greeting}
            </motion.p>
          </div>
        </div>
      ) : (
        <div className="flex min-w-0 flex-col items-start gap-1">
          {cfg.showTierChip && <TierChip />}
          <motion.p
            id="home-hero-greeting"
            className="text-lg font-extrabold text-gray-900"
            initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
          >
            {greeting}
          </motion.p>
        </div>
      )}

      <div className="mt-3">
        {next.isLoading ? (
          <div className="h-16 animate-pulse rounded-3xl bg-brand-100" aria-hidden="true" />
        ) : next.mode === 'caught_up' || !next.to ? (
          cfg.heroVariant === 'flat' ? (
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white p-5 text-gray-900 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider opacity-90">All caught up</p>
              <p className="mt-1 text-lg font-extrabold">You've finished everything for now!</p>
              <GradientButton
                to={dueCount > 0 ? '/progress' : '/lessons'}
                full
                className="mt-4 !bg-none bg-brand-700 text-white shadow-none hover:bg-brand-800"
              >
                {dueCount > 0 ? 'Review concepts' : 'Explore modules'}<span aria-hidden="true"> →</span>
              </GradientButton>
            </div>
          ) : (
            <div className="overflow-hidden rounded-3xl bg-brand-gradient p-5 text-white shadow-lg shadow-brand-600/30">
              <p className="text-xs font-bold uppercase tracking-wider opacity-90"><span aria-hidden="true">🎉 </span>All caught up</p>
              <p className="mt-1 text-lg font-extrabold">You've finished everything for now!</p>
              <GradientButton
                to={dueCount > 0 ? '/progress' : '/lessons'}
                full
                className="mt-4 !bg-none bg-white text-brand-700 shadow-none hover:bg-brand-50"
              >
                {dueCount > 0 ? 'Review concepts' : 'Explore modules'}<span aria-hidden="true"> →</span>
              </GradientButton>
            </div>
          )
        ) : (
          <HeroCard
            onCtaClick={() => track('home_cta_tap', { surface: 'hero' })}
            eyebrow={next.mode === 'continue' ? (cfg.heroVariant === 'flat' ? 'Continue' : 'Continue learning') : 'Start here'}
            icon={next.moduleIcon ?? '📈'}
            title={next.lessonLabel ?? 'Your next lesson'}
            subtitle={next.moduleTitle ?? undefined}
            cta={next.mode === 'continue' ? 'Continue' : 'Start lesson'}
            to={next.to!}
            variant={cfg.heroVariant}
          />
        )}
      </div>
    </section>
  );
}
