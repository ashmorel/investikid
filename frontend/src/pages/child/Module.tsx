import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentApi, type LevelOut, type ModuleOut } from '@/api/content';
import { LevelCard } from '@/components/child/LevelCard';
import { BackButton } from '@/components/child/BackButton';
import { useToast } from '@/hooks/use-toast';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { dismissNudge, isNudgeDismissed } from '@/lib/premiumNudge';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

export default function Module() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { open: openPaywall } = usePremiumPaywall();
  const nudgeKey = 'level-nudge:' + moduleId;
  const tier = useAgeTier();
  // Investor tier celebrates quietly: same banners and buttons, plainer emoji-free copy.
  const subtle = tierConfig[tier].celebration === 'subtle';
  const [nudgeDismissed, setNudgeDismissed] = useState(() => isNudgeDismissed(nudgeKey));

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false, staleTime: 60_000,
  });

  const levelsQ = useQuery<LevelOut[] | null>({
    queryKey: ['module-levels', moduleId],
    queryFn: () => contentApi.listLevels(moduleId!),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });

  if (modulesQ.isLoading || levelsQ.isLoading) {
    return <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6 text-sm text-gray-500">Loading…</div>;
  }

  if (modulesQ.isError || levelsQ.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
        <BackButton to="/lessons" label="Modules" />
        <p className="mt-2">Module not found or locked.</p>
      </div>
    );
  }

  const module = (modulesQ.data ?? []).find((m) => m.id === moduleId);
  const levels = (levelsQ.data ?? []) as LevelOut[];

  // Single-level modules read as "lessons" (not a misleading "1 of 1 levels").
  const single = levels.length === 1;
  const allComplete = levels.length > 0 && levels.every((l) => l.state === 'completed');
  const totalLessons = levels.reduce((n, l) => n + l.lessons_total, 0);
  const doneLessons = levels.reduce((n, l) => n + l.lessons_completed, 0);
  const progressDone = single ? doneLessons : levels.filter((l) => l.state === 'completed').length;
  const progressTotal = single ? totalLessons : levels.length;
  const unit = single ? 'lesson' : 'level';
  // Earned moment: the child finished their free levels and the next is premium-locked.
  const orderedLevels = [...levels].sort((a, b) => a.order_index - b.order_index);
  const nextPremiumLevel = orderedLevels.find(
    (l, i) =>
      l.state === 'locked' &&
      l.locked_reason === 'premium' &&
      orderedLevels.slice(0, i).every((p) => p.state === 'completed'),
  );
  const showEarnedNudge = !!nextPremiumLevel && !nudgeDismissed;
  // Next module by order (for the "what's next" CTA after finishing).
  const nextModule = module
    ? [...(modulesQ.data ?? [])]
        .sort((a, b) => a.order_index - b.order_index)
        .find((m) => m.order_index > module.order_index)
    : undefined;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="px-4 pt-4 sm:px-6">
        <BackButton to="/lessons" label="Modules" />
      </div>
      {/* Banner */}
      <div className="bg-gradient-to-br from-brand-100 to-brand-200 px-4 py-6 sm:px-6 sm:py-8 text-center">
        <span className="text-5xl">{module?.icon ?? '📚'}</span>
        <h1 className="mt-3 text-2xl font-extrabold text-gray-900">{module?.title ?? 'Module'}</h1>
        <p className="mt-1 text-sm text-gray-600">
          {progressTotal} {progressTotal === 1 ? unit : `${unit}s`}
        </p>
        {progressTotal > 0 && (() => {
          const pct = Math.round((progressDone / progressTotal) * 100);
          return (
            <div className="mx-auto mt-3 max-w-xs">
              <div
                className="h-2 w-full overflow-hidden rounded-full bg-white/60"
                role="progressbar"
                aria-valuenow={progressDone}
                aria-valuemin={0}
                aria-valuemax={progressTotal}
                aria-label="Module progress"
              >
                <div className="h-full rounded-full bg-brand-gradient" style={{ width: `${pct}%` }} />
              </div>
              <p className="mt-1 text-xs font-semibold text-brand-700">
                {progressDone} / {progressTotal} {unit}s complete
              </p>
            </div>
          );
        })()}
      </div>

      {/* Level list */}
      <div className="px-4 py-4 sm:px-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {levels.map((level) => (
            <LevelCard
              key={level.id}
              level={level}
              onOpen={() => navigate(`/lessons/${moduleId}/${level.id}`)}
              onLockedClick={() => {
                if (level.locked_reason === 'premium') {
                  openPaywall({ kind: 'level', label: level.title });
                } else {
                  toast({ title: 'Locked', description: 'Finish the previous level first.' });
                }
              }}
            />
          ))}
        </div>
      </div>

      {/* Earned moment: free levels done, next level is premium-locked. */}
      {showEarnedNudge && nextPremiumLevel && (
        <div className="px-4 pb-6 sm:px-6">
          <div className="relative rounded-2xl border-2 border-accent-200 bg-accent-50 p-4 text-center">
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => {
                dismissNudge(nudgeKey);
                setNudgeDismissed(true);
              }}
              className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-black/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
            >
              ✕
            </button>
            <p className="text-base font-bold text-gray-900">
              {subtle ? `You're ready for ${nextPremiumLevel.title}.` : `🎉 You're ready for ${nextPremiumLevel.title}!`}
            </p>
            <p className="mt-1 text-sm text-gray-600">
              {subtle ? 'Premium unlocks the next level.' : 'Unlock Premium to keep going 🌟'}
            </p>
            <button
              type="button"
              onClick={() => openPaywall({ kind: 'level', label: nextPremiumLevel.title })}
              className="mt-3 inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              {subtle ? 'Ask my grown-up' : 'Ask my grown-up ✨'}
            </button>
          </div>
        </div>
      )}

      {/* Module complete → what's next */}
      {!showEarnedNudge && allComplete && (
        <div className="px-4 pb-6 sm:px-6">
          <div className="rounded-2xl border-2 border-brand-200 bg-brand-50 p-4 text-center">
            <p className="text-base font-bold text-gray-900">
              {subtle ? 'Module complete.' : '🎉 Module complete!'}
            </p>
            <p className="mt-1 text-sm text-gray-600">
              {subtle
                ? `Great work on ${module?.title ?? 'this module'}.`
                : `Great work finishing ${module?.title ?? 'this module'}.`}
            </p>
            <button
              type="button"
              onClick={() => navigate(nextModule ? `/lessons/${nextModule.id}` : '/lessons')}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              {nextModule ? `Next: ${nextModule.title} →` : 'Back to all modules'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
