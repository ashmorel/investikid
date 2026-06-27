import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useReducedMotion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { contentApi, type LevelOut, type ModuleOut } from '@/api/content';
import type { Me } from '@/api/auth';
import { scopeFromMe } from '@/lib/offline/scope';
import { cacheFirst } from '@/lib/offline/useOfflineContent';
import * as offlineStore from '@/lib/offline/contentStore';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';
import { celebrate } from '@/lib/confetti';
import { LevelCard } from '@/components/child/LevelCard';
import { useOfflineAvailability } from '@/hooks/useOfflineAvailability';
import { BackButton } from '@/components/child/BackButton';
import { useToast } from '@/hooks/use-toast';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { dismissNudge, isNudgeDismissed } from '@/lib/premiumNudge';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

export default function Module() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { t } = useTranslation('lessons');
  const { open: openPaywall } = usePremiumPaywall();
  const nudgeKey = 'level-nudge:' + moduleId;
  const tier = useAgeTier();
  // Investor tier celebrates quietly: same banners and buttons, plainer emoji-free copy.
  const subtle = tierConfig[tier].celebration === 'subtle';
  const [nudgeDismissed, setNudgeDismissed] = useState(() => isNudgeDismissed(nudgeKey));
  const reducedMotion = useReducedMotion();
  const qc = useQueryClient();
  const scope = scopeFromMe(qc.getQueryData<Me>(['me']));
  const offlineAvailability = useOfflineAvailability();

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: cacheFirst({
      scope,
      fetch: () => contentApi.listModules(),
      read: (s) => offlineStore.getModules(s),
      write: (s, data) => offlineStore.upsertModules(s, data ?? []),
    }),
    retry: false, staleTime: 60_000,
  });

  const levelsQ = useQuery<LevelOut[] | null>({
    queryKey: ['module-levels', moduleId],
    queryFn: cacheFirst({
      scope,
      fetch: () => contentApi.listLevels(moduleId!),
      read: (s) => offlineStore.getModuleLevels(s, moduleId!),
      write: (s, data) => offlineStore.upsertModuleLevels(s, moduleId!, data ?? []),
    }),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });

  const levels = (levelsQ.data ?? []) as LevelOut[];
  const allComplete = levels.length > 0 && levels.every((l) => l.state === 'completed');
  // Earned moment: the child finished their free levels and the next is premium-locked.
  const orderedLevels = [...levels].sort((a, b) => a.order_index - b.order_index);
  const nextPremiumLevel = orderedLevels.find(
    (l, i) =>
      l.state === 'locked' &&
      l.locked_reason === 'premium' &&
      orderedLevels.slice(0, i).every((p) => p.state === 'completed'),
  );
  const showEarnedNudge = !!nextPremiumLevel && !nudgeDismissed;
  const showCompleteBanner = !showEarnedNudge && allComplete;

  // Mastery moment (juice pack, spec C): once per visit when the module-complete
  // banner appears. Confetti is explorers-only and skipped under reduced motion.
  const masteryFired = useRef(false);
  useEffect(() => {
    if (!showCompleteBanner || masteryFired.current) return;
    masteryFired.current = true;
    playSound('mastery');
    void haptic('heavy');
    if (!subtle && !reducedMotion) celebrate();
  }, [showCompleteBanner, subtle, reducedMotion]);

  if (modulesQ.isLoading || levelsQ.isLoading) {
    return <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6 text-sm text-gray-500">{t('module.loading')}</div>;
  }

  if (modulesQ.isError || levelsQ.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
        <BackButton to="/lessons" label={t('modules.heading')} />
        <p className="mt-2">{t('module.notFound')}</p>
      </div>
    );
  }

  const module = (modulesQ.data ?? []).find((m) => m.id === moduleId);

  // Single-level modules read as "lessons" (not a misleading "1 of 1 levels").
  const single = levels.length === 1;
  const totalLessons = levels.reduce((n, l) => n + l.lessons_total, 0);
  const doneLessons = levels.reduce((n, l) => n + l.lessons_completed, 0);
  const progressDone = single ? doneLessons : levels.filter((l) => l.state === 'completed').length;
  const progressTotal = single ? totalLessons : levels.length;
  const unit = single ? 'lesson' : 'level';
  // Next module by order (for the "what's next" CTA after finishing).
  const nextModule = module
    ? [...(modulesQ.data ?? [])]
        .sort((a, b) => a.order_index - b.order_index)
        .find((m) => m.order_index > module.order_index)
    : undefined;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="px-4 pt-4 sm:px-6">
        <BackButton to="/lessons" label={t('modules.heading')} />
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
                aria-label={t('module.progress.ariaLabel')}
              >
                <div className="h-full rounded-full bg-brand-gradient" style={{ width: `${pct}%` }} />
              </div>
              <p className="mt-1 text-xs font-semibold text-brand-700">
                {t('module.progress.complete', { done: progressDone, total: progressTotal, unit })}
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
              isOfflineAvailable={offlineAvailability.levelIds.has(level.id)}
              onOpen={() => navigate(`/lessons/${moduleId}/${level.id}`)}
              onLockedClick={() => {
                if (level.locked_reason === 'premium') {
                  openPaywall({ kind: 'level', label: level.title });
                } else {
                  toast({ title: t('module.locked.title'), description: t('module.locked.description') });
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
              aria-label={t('module.earnedNudge.dismiss')}
              onClick={() => {
                dismissNudge(nudgeKey);
                setNudgeDismissed(true);
              }}
              className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-black/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
            >
              {t('module.earnedNudge.dismissIcon')}
            </button>
            <p className="text-base font-bold text-gray-900">
              {subtle
                ? t('module.earnedNudge.readySubtle', { title: nextPremiumLevel.title })
                : t('module.earnedNudge.readyFun', { title: nextPremiumLevel.title })}
            </p>
            <p className="mt-1 text-sm text-gray-600">
              {subtle ? t('module.earnedNudge.premiumSubtle') : t('module.earnedNudge.premiumFun')}
            </p>
            <button
              type="button"
              onClick={() => openPaywall({ kind: 'level', label: nextPremiumLevel.title })}
              className="mt-3 inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              {subtle ? t('module.earnedNudge.ctaSubtle') : t('module.earnedNudge.ctaFun')}
            </button>
          </div>
        </div>
      )}

      {/* Module complete → what's next */}
      {showCompleteBanner && (
        <div className="px-4 pb-6 sm:px-6">
          <div className="rounded-2xl border-2 border-brand-200 bg-brand-50 p-4 text-center">
            <p className="text-base font-bold text-gray-900">
              {subtle ? t('module.completeBanner.titleSubtle') : t('module.completeBanner.titleFun')}
            </p>
            <p className="mt-1 text-sm text-gray-600">
              {subtle
                ? t('module.completeBanner.bodySubtle', { title: module?.title ?? 'this module' })
                : t('module.completeBanner.bodyFun', { title: module?.title ?? 'this module' })}
            </p>
            <button
              type="button"
              onClick={() => navigate(nextModule ? `/lessons/${nextModule.id}` : '/lessons')}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              {nextModule
                ? t('module.completeBanner.nextCta', { title: nextModule.title })
                : t('module.completeBanner.backCta')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
