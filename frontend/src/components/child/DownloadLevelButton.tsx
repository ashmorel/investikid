// frontend/src/components/child/DownloadLevelButton.tsx
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Download, CheckCircle2 } from 'lucide-react';
import type { LessonSummary } from '@/api/content';
import { contentApi } from '@/api/content';
import type { Me } from '@/api/auth';
import { scopeFromMe } from '@/lib/offline/scope';
import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import { upsertLesson } from '@/lib/offline/contentStore';
import { useOfflineAvailability } from '@/hooks/useOfflineAvailability';
import { useOnline } from '@/hooks/useOnline';

type Props = {
  levelId: string;
  lessons: LessonSummary[];
};

export function DownloadLevelButton({ levelId, lessons }: Props) {
  const { t } = useTranslation('child');
  const qc = useQueryClient();
  const online = useOnline();
  const { levelIds } = useOfflineAvailability();
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);

  // Only render on native devices with SQLite
  if (!isOfflineDbAvailable()) return null;

  const scope = scopeFromMe(qc.getQueryData<Me>(['me']));
  if (!scope) return null;

  const alreadyAvailable = levelIds.has(levelId);

  // Hidden when offline and not yet saved
  if (!online && !alreadyAvailable) return null;

  if (alreadyAvailable) {
    return (
      <div
        role="status"
        className="mt-3 flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700"
      >
        <CheckCircle2 size={16} aria-hidden="true" />
        <span>{t('offline.available')}</span>
      </div>
    );
  }

  async function handleDownload() {
    if (busy || !scope) return;
    setBusy(true);
    setDone(0);
    setTotal(lessons.length);
    try {
      for (let i = 0; i < lessons.length; i++) {
        const lesson = await contentApi.getLesson(lessons[i].id);
        if (lesson) {
          await upsertLesson(scope, lesson, levelId);
        }
        setDone(i + 1);
      }
    } finally {
      setBusy(false);
      void qc.invalidateQueries({ queryKey: ['offline-availability'] });
    }
  }

  if (busy) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="mt-3 rounded-2xl border border-brand-200 bg-brand-50 px-4 py-2.5"
      >
        <p className="text-sm font-semibold text-brand-700">
          {t('offline.saving', { done, total })}
        </p>
        <div
          className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-brand-100"
          role="progressbar"
          aria-valuenow={done}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-label={t('offline.saving', { done, total })}
        >
          <div
            className="h-full rounded-full bg-brand-gradient transition-all"
            style={{ width: total > 0 ? `${Math.round((done / total) * 100)}%` : '0%' }}
          />
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={handleDownload}
      className="mt-3 flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-100 active:opacity-80 transition-colors"
    >
      <Download size={16} aria-hidden="true" />
      <span>{t('offline.download')}</span>
    </button>
  );
}
