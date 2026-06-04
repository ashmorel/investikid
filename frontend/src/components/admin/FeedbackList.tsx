import { useState } from 'react';
import { useFeedback } from '@/api/admin';

const TYPE_BADGE: Record<string, string> = {
  bug: 'bg-danger-100 text-danger-700',
  feature: 'bg-info-100 text-info-600',
  general: 'bg-brand-50 text-ink',
};

const TYPE_LABEL: Record<string, string> = {
  bug: 'Bug',
  feature: 'Feature',
  general: 'General',
};

export default function FeedbackList() {
  const [type, setType] = useState('');
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useFeedback({ type: type || undefined, page });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1;

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-ink">Feedback</h1>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <label htmlFor="feedback-type-filter">Filter</label>
          <select
            id="feedback-type-filter"
            className="rounded-md border border-input bg-background px-2 py-1 text-sm text-ink"
            value={type}
            onChange={(e) => { setType(e.target.value); setPage(1); }}
          >
            <option value="">All</option>
            <option value="bug">Bug</option>
            <option value="feature">Feature</option>
            <option value="general">General</option>
          </select>
        </div>
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {isError && <p className="text-danger-500">Failed to load feedback.</p>}

      {data && (
        <>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left text-muted-foreground">
                <th className="py-2 pr-4">Date</th>
                <th className="py-2 pr-4">User</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Message</th>
                <th className="py-2 pr-4">Page</th>
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
                      {TYPE_LABEL[f.feedback_type] ?? f.feedback_type}
                    </span>
                  </td>
                  <td className="py-2 pr-4 max-w-md">{f.message}</td>
                  <td className="py-2 pr-4 text-muted-foreground">{f.page_url ?? '—'}</td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center text-muted-foreground">No feedback yet.</td></tr>
              )}
            </tbody>
          </table>

          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <button
              className="rounded border border-line px-3 py-1 disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span>Page {page} of {totalPages}</span>
            <button
              className="rounded border border-line px-3 py-1 disabled:opacity-40"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
