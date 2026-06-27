// frontend/src/pages/child/Downloaded.tsx
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CloudDownload, DownloadCloud, Trash2 } from 'lucide-react';
import type { Me } from '@/api/auth';
import { scopeFromMe } from '@/lib/offline/scope';
import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import { listDownloadedLevels, removeLevel, type DownloadedLevel } from '@/lib/offline/contentStore';

function useDownloadedLevels() {
  const qc = useQueryClient();
  const scope = scopeFromMe(qc.getQueryData<Me>(['me']));
  return useQuery<DownloadedLevel[]>({
    queryKey: ['downloaded-levels', scope?.childId, scope?.market],
    queryFn: () => listDownloadedLevels(scope!),
    enabled: isOfflineDbAvailable() && !!scope,
    staleTime: 60_000,
  });
}

export default function Downloaded() {
  const { t } = useTranslation('child');
  const qc = useQueryClient();
  const scope = scopeFromMe(qc.getQueryData<Me>(['me']));
  const { data: levels = [] } = useDownloadedLevels();

  async function handleRemove(levelId: string) {
    if (scope) await removeLevel(scope, levelId);
    void qc.invalidateQueries({ queryKey: ['downloaded-levels'] });
    void qc.invalidateQueries({ queryKey: ['offline-availability'] });
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
      <div className="mb-6 flex items-center gap-3">
        <DownloadCloud className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <h1 className="text-xl font-bold text-gray-900">{t('offline.downloadedTitle')}</h1>
      </div>

      {levels.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-brand-200 bg-brand-50 px-6 py-12 text-center">
          <CloudDownload className="h-12 w-12 text-brand-400" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-gray-900">{t('offline.emptyTitle')}</h2>
          <p className="text-sm text-gray-600">{t('offline.emptyBody')}</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {levels.map((level) => (
            <li
              key={level.levelId}
              className="flex items-center justify-between rounded-2xl border border-brand-200 bg-brand-50 px-4 py-3"
            >
              <div>
                <p className="font-semibold text-gray-900">{level.title}</p>
                <p className="text-sm text-brand-700">
                  {t('offline.lessonsSaved', { count: level.lessonCount })}
                </p>
              </div>
              <button
                type="button"
                aria-label={t('offline.remove')}
                onClick={() => void handleRemove(level.levelId)}
                className="ml-4 flex h-10 w-10 items-center justify-center rounded-full border border-brand-200 bg-white text-brand-700 hover:bg-brand-100"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
