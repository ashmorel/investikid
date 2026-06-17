import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useFeedback } from '@/api/admin';

const TYPE_BADGE: Record<string, string> = {
  bug: 'bg-danger-100 text-danger-700',
  feature: 'bg-info-100 text-info-600',
  general: 'bg-brand-50 text-ink',
};


export default function FeedbackList() {
  const { t } = useTranslation('admin');
  const [type, setType] = useState('');
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useFeedback({ type: type || undefined, page });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1;

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-ink">{t('feedbackList.heading')}</h1>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <label htmlFor="feedback-type-filter">{t('feedbackList.filter')}</label>
          <select
            id="feedback-type-filter"
            className="rounded-md border border-input bg-background px-2 py-1 text-sm text-ink"
            value={type}
            onChange={(e) => { setType(e.target.value); setPage(1); }}
          >
            <option value="">{t('feedbackList.filterAll')}</option>
            <option value="bug">{t('feedbackList.filterBug')}</option>
            <option value="feature">{t('feedbackList.filterFeature')}</option>
            <option value="general">{t('feedbackList.filterGeneral')}</option>
          </select>
        </div>
      </div>

      {isLoading && <p className="text-muted-foreground">{t('feedbackList.loading')}</p>}
      {isError && <p className="text-danger-500">{t('feedbackList.error')}</p>}

      {data && (
        <>
          <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left text-muted-foreground">
                <th className="py-2 pr-4">{t('feedbackList.table.date')}</th>
                <th className="py-2 pr-4">{t('feedbackList.table.user')}</th>
                <th className="py-2 pr-4">{t('feedbackList.table.type')}</th>
                <th className="py-2 pr-4">{t('feedbackList.table.message')}</th>
                <th className="py-2 pr-4">{t('feedbackList.table.page')}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((f) => (
                <tr key={f.id} className="border-b border-line align-top text-ink">
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {new Date(f.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {f.submitter}
                    <span className="ml-1 text-xs text-muted-foreground">({f.submitter_role})</span>
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${TYPE_BADGE[f.feedback_type] ?? ''}`}>
                      {t(`feedbackList.typeLabel.${f.feedback_type}`, f.feedback_type)}
                    </span>
                  </td>
                  <td className="py-2 pr-4 max-w-md">{f.message}</td>
                  <td className="py-2 pr-4 text-muted-foreground">{f.page_url ?? '—'}</td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center text-muted-foreground">{t('feedbackList.noFeedback')}</td></tr>
              )}
            </tbody>
          </table>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <button
              className="rounded border border-line px-3 py-1 disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              {t('feedbackList.previous')}
            </button>
            <span>{t('feedbackList.pageOf', { page, total: totalPages })}</span>
            <button
              className="rounded border border-line px-3 py-1 disabled:opacity-40"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              {t('feedbackList.next')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
