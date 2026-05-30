import { useState } from 'react';
import { useFeedback } from '@/api/admin';

const TYPE_BADGE: Record<string, string> = {
  bug: 'bg-red-100 text-red-800',
  feature: 'bg-blue-100 text-blue-800',
  general: 'bg-slate-100 text-slate-800',
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
        <h1 className="text-xl font-bold text-slate-50">Feedback</h1>
        <label className="text-sm text-slate-300">
          <span className="mr-2">Filter</span>
          <select
            className="rounded-md border border-slate-600 bg-slate-800 px-2 py-1 text-sm text-slate-100"
            value={type}
            onChange={(e) => { setType(e.target.value); setPage(1); }}
          >
            <option value="">All</option>
            <option value="bug">Bug</option>
            <option value="feature">Feature</option>
            <option value="general">General</option>
          </select>
        </label>
      </div>

      {isLoading && <p className="text-slate-400">Loading…</p>}
      {isError && <p className="text-red-400">Failed to load feedback.</p>}

      {data && (
        <>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-slate-400">
                <th className="py-2 pr-4">Date</th>
                <th className="py-2 pr-4">User</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Message</th>
                <th className="py-2 pr-4">Page</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((f) => (
                <tr key={f.id} className="border-b border-slate-800 align-top text-slate-200">
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {new Date(f.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {f.submitter}
                    <span className="ml-1 text-xs text-slate-500">({f.submitter_role})</span>
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${TYPE_BADGE[f.feedback_type] ?? ''}`}>
                      {TYPE_LABEL[f.feedback_type] ?? f.feedback_type}
                    </span>
                  </td>
                  <td className="py-2 pr-4 max-w-md">{f.message}</td>
                  <td className="py-2 pr-4 text-slate-400">{f.page_url ?? '—'}</td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center text-slate-500">No feedback yet.</td></tr>
              )}
            </tbody>
          </table>

          <div className="mt-4 flex items-center justify-between text-sm text-slate-300">
            <button
              className="rounded border border-slate-600 px-3 py-1 disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span>Page {page} of {totalPages}</span>
            <button
              className="rounded border border-slate-600 px-3 py-1 disabled:opacity-40"
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
