import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentApi, type LevelOut, type ModuleOut } from '@/api/content';
import { LevelCard } from '@/components/child/LevelCard';
import { BackButton } from '@/components/child/BackButton';
import { useToast } from '@/hooks/use-toast';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';

export default function Module() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { open: openPaywall } = usePremiumPaywall();

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
          {levels.length} {levels.length === 1 ? 'level' : 'levels'}
        </p>
        {levels.length > 0 && (() => {
          const done = levels.filter((l) => l.state === 'completed').length;
          const pct = Math.round((done / levels.length) * 100);
          return (
            <div className="mx-auto mt-3 max-w-xs">
              <div
                className="h-2 w-full overflow-hidden rounded-full bg-white/60"
                role="progressbar"
                aria-valuenow={done}
                aria-valuemin={0}
                aria-valuemax={levels.length}
                aria-label="Module progress"
              >
                <div className="h-full rounded-full bg-brand-gradient" style={{ width: `${pct}%` }} />
              </div>
              <p className="mt-1 text-xs font-semibold text-brand-700">{done} / {levels.length} levels complete</p>
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
    </div>
  );
}
