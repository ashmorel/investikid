import { useQueries, useQuery } from '@tanstack/react-query';
import { contentApi, type LessonSummary, type ModuleOut } from '@/api/content';
import { ModuleCard } from '@/components/child/ModuleCard';
import { RegionSwitcher } from '@/components/child/RegionSwitcher';
import { authApi, type Me } from '@/api/auth';
import type { RegionCode } from '@/lib/region';
import { orderModulesForTier } from '@/lib/tierModuleOrder';
import { DEFAULT_TIER, densityGridGap, tierConfig } from '@/lib/ageTier';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';

export default function Lessons() {
  const { open: openPaywall } = usePremiumPaywall();

  const { data: me } = useQuery<Me | null>({ queryKey: ['me'], queryFn: () => authApi.me(), staleTime: 60_000 });
  const currentRegion = (me?.content_region ?? me?.country_code ?? 'US') as RegionCode;

  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false,
    staleTime: 60_000,
  });

  const tier = me?.age_tier ?? DEFAULT_TIER;
  const modules = orderModulesForTier(modulesQ.data ?? [], tier);

  const lessonQueries = useQueries({
    queries: modules.filter((m) => !m.locked).map((m) => ({
      queryKey: ['module', m.id, 'lessons'],
      queryFn: () => contentApi.listLessons(m.id),
      retry: false,
      staleTime: 60_000,
    })),
  });

  const lessonsByModuleId = new Map<string, LessonSummary[]>();
  let qIdx = 0;
  for (const m of modules) {
    if (m.locked) {
      lessonsByModuleId.set(m.id, []);
    } else {
      const data = (lessonQueries[qIdx]?.data ?? []) as LessonSummary[];
      lessonsByModuleId.set(m.id, data);
      qIdx++;
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-4 sm:px-6 sm:py-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-extrabold text-gray-900">Modules</h1>
        <RegionSwitcher currentRegion={currentRegion} />
      </div>
      <p className="mt-1 text-sm text-gray-500">{modules.length} modules · {modules.reduce((acc, m) => acc + (lessonsByModuleId.get(m.id)?.length ?? 0), 0)} lessons</p>
      {modules.length > 0 && (() => {
        const started = modules.filter((m) => (lessonsByModuleId.get(m.id) ?? []).some((l) => l.completed)).length;
        const pct = Math.round((started / modules.length) * 100);
        return (
          <div className="mt-4 rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
            <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
              <span>Your journey</span>
              <span>{started} / {modules.length} modules started</span>
            </div>
            <div
              className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
              role="progressbar"
              aria-valuenow={started}
              aria-valuemin={0}
              aria-valuemax={modules.length}
              aria-label="Modules started"
            >
              <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })()}
      <div className={`mt-5 grid grid-cols-1 ${densityGridGap[tierConfig[tier].density]} sm:grid-cols-2 md:grid-cols-3`}>
        {modules.map((m) => {
          const lessons = lessonsByModuleId.get(m.id) ?? [];
          const completedCount = lessons.filter((l) => l.completed).length;
          return (
            <ModuleCard
              key={m.id}
              module={m}
              completedCount={completedCount}
              totalCount={lessons.length}
              onLockedClick={() => openPaywall({ kind: 'module', label: m.title })}
            />
          );
        })}
      </div>
    </div>
  );
}
