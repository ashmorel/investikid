import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentApi, type LevelOut, type ModuleOut } from '@/api/content';
import { LevelCard } from '@/components/child/LevelCard';
import { useToast } from '@/hooks/use-toast';

export default function Module() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

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
        <p>Module not found or locked.</p>
        <Link to="/lessons" className="text-sm text-amber-600 hover:underline">← Back to modules</Link>
      </div>
    );
  }

  const module = (modulesQ.data ?? []).find((m) => m.id === moduleId);
  const levels = (levelsQ.data ?? []) as LevelOut[];

  return (
    <div className="mx-auto max-w-3xl">
      {/* Banner */}
      <div className="bg-gradient-to-br from-amber-100 to-amber-200 px-4 py-6 sm:px-6 sm:py-8 text-center">
        <span className="text-5xl">{module?.icon ?? '📚'}</span>
        <h1 className="mt-3 text-2xl font-extrabold text-gray-900">{module?.title ?? 'Module'}</h1>
        <p className="mt-1 text-sm text-gray-600">
          {levels.length} {levels.length === 1 ? 'level' : 'levels'}
        </p>
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
                  toast({ title: 'Premium', description: 'Ask a grown-up to unlock.' });
                } else {
                  toast({ title: 'Locked', description: 'Finish the previous level first.' });
                }
              }}
            />
          ))}
        </div>
        <Link to="/lessons" className="mt-4 inline-block text-sm text-amber-600 hover:underline">← Back to modules</Link>
      </div>
    </div>
  );
}
