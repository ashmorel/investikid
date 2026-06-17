import { useTranslation } from 'react-i18next';
import { useModuleEngagement } from '@/api/admin';
import type { LessonEngagement } from '@/api/admin';

function pct(v: number | null): string {
  return v == null ? '—' : `${Math.round(v * 100)}%`;
}
function score(v: number | null): string {
  return v == null ? '—' : `${Math.round(v * 100)}%`;
}

export default function ModuleEngagement({ moduleId }: { moduleId: string }) {
  const { t } = useTranslation('admin');
  const { data, isLoading, isError } = useModuleEngagement(moduleId);

  if (isLoading) return <p className="text-muted-foreground">{t('moduleEngagement.loading')}</p>;
  if (isError || !data) return <p className="text-muted-foreground">{t('moduleEngagement.unavailable')}</p>;
  if (data.learners_started === 0) {
    return <p className="text-muted-foreground">{t('moduleEngagement.noData')}</p>;
  }

  // Highlight the lesson with the lowest completion rate (the sticking point).
  const worst = data.lessons
    .filter((l) => l.completion_rate != null)
    .reduce<LessonEngagement | null>(
      (acc, l) => (acc == null || l.completion_rate! < acc.completion_rate! ? l : acc),
      null,
    )?.lesson_id ?? null;

  return (
    <section aria-labelledby="engagement-heading" className="mt-6">
      <h3 id="engagement-heading" className="mb-3 text-lg font-semibold text-ink">{t('moduleEngagement.heading')}</h3>

      <dl className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-line bg-card p-3">
          <dt className="text-xs text-muted-foreground">{t('moduleEngagement.learnersStarted')}</dt>
          <dd className="text-xl font-semibold text-ink">{data.learners_started}</dd>
        </div>
        <div className="rounded-md border border-line bg-card p-3">
          <dt className="text-xs text-muted-foreground">{t('moduleEngagement.completedModule')}</dt>
          <dd className="text-xl font-semibold text-ink">{pct(data.completion_rate)}</dd>
        </div>
        <div className="rounded-md border border-line bg-card p-3">
          <dt className="text-xs text-muted-foreground">{t('moduleEngagement.avgScore')}</dt>
          <dd className="text-xl font-semibold text-ink">{score(data.average_score)}</dd>
        </div>
      </dl>

      <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{t('moduleEngagement.tableCaption')}</caption>
        <thead className="text-xs text-muted-foreground">
          <tr>
            <th scope="col" className="py-1 pr-2">{t('moduleEngagement.colLesson')}</th>
            <th scope="col" className="py-1 pr-2">{t('moduleEngagement.colViews')}</th>
            <th scope="col" className="py-1 pr-2">{t('moduleEngagement.colCompleted')}</th>
            <th scope="col" className="py-1 pr-2">{t('moduleEngagement.colRate')}</th>
            <th scope="col" className="py-1 pr-2">{t('moduleEngagement.colAvgScore')}</th>
            <th scope="col" className="py-1 pr-2">{t('moduleEngagement.colDropOff')}</th>
          </tr>
        </thead>
        <tbody>
          {data.lessons.map((l) => (
            <tr key={l.lesson_id} className={l.lesson_id === worst ? 'bg-brand-500/10' : ''}>
              <td className="py-1 pr-2 text-ink">{l.label}</td>
              <td className="py-1 pr-2 text-muted-foreground">{l.views}</td>
              <td className="py-1 pr-2 text-muted-foreground">{l.completions}</td>
              <td className="py-1 pr-2 text-muted-foreground">{pct(l.completion_rate)}</td>
              <td className="py-1 pr-2 text-muted-foreground">{l.type === 'quiz' || l.type === 'scenario' ? score(l.average_score) : '—'}</td>
              <td className="py-1 pr-2 text-muted-foreground">{l.drop_off > 0 ? `−${l.drop_off}` : '0'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </section>
  );
}
