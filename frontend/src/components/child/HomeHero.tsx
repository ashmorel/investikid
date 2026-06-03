import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useNextLesson } from '@/hooks/useNextLesson';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { useRecommendations, useHomeGreeting } from '@/api/ai';
import { buildHeroGreeting } from '@/lib/homeHero';

export default function HomeHero() {
  const next = useNextLesson();
  const { data: me } = useChildSession();
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();

  const name = me?.username ?? 'there';
  const streakCount = progress?.streak_count ?? 0;
  const dueCount = recs?.review_summary?.due_count ?? 0;
  const isPremium = me?.is_premium ?? false;

  const templated = buildHeroGreeting({ name, mode: next.mode, lessonLabel: next.lessonLabel, streakCount, dueCount });

  const aiQ = useHomeGreeting(
    { name, mode: next.mode, lesson_label: next.lessonLabel, streak_count: streakCount, due_count: dueCount },
    isPremium && !next.isLoading,
  );
  const greeting = (isPremium && aiQ.data?.greeting) ? aiQ.data.greeting : templated;

  const ctaLabel = next.mode === 'continue' ? 'Continue' : 'Start';

  return (
    <section aria-labelledby="home-hero-greeting" className="mb-2">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-amber-100 text-2xl shadow" aria-hidden="true">💡</div>
        <motion.p
          id="home-hero-greeting"
          className="rounded-2xl rounded-tl-sm border border-amber-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-800 shadow-sm"
          initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        >
          {greeting}
        </motion.p>
      </div>

      <motion.div
        className="mt-3 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 p-5 text-white shadow-lg"
        initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35, delay: 0.05 }}
      >
        {next.isLoading ? (
          <div className="h-16 animate-pulse rounded-xl bg-white/30" aria-hidden="true" />
        ) : next.mode === 'caught_up' || !next.to ? (
          <div>
            <p className="text-xs font-bold uppercase tracking-wider opacity-90"><span aria-hidden="true">🎉 </span>All caught up</p>
            <p className="mt-1 text-lg font-extrabold">You've finished everything for now!</p>
            <Link to={dueCount > 0 ? '/progress' : '/lessons'}
              className="mt-3 inline-block rounded-xl bg-white px-5 py-2.5 text-sm font-extrabold text-amber-700 shadow">
              {dueCount > 0 ? 'Review concepts →' : 'Explore modules →'}
            </Link>
          </div>
        ) : (
          <div>
            <p className="text-xs font-bold uppercase tracking-wider opacity-90"><span aria-hidden="true">▶ </span>{ctaLabel === 'Continue' ? 'Pick up where you left off' : 'Start here'}</p>
            <p className="mt-1 text-lg font-extrabold leading-tight">
              <span aria-hidden="true">{next.moduleIcon} </span>{next.lessonLabel}
            </p>
            <Link to={next.to}
              className="mt-3 inline-block rounded-xl bg-white px-5 py-2.5 text-sm font-extrabold text-amber-700 shadow hover:bg-amber-50">
              {ctaLabel} →
            </Link>
          </div>
        )}
      </motion.div>
    </section>
  );
}
