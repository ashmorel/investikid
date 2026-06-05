import { Link } from 'react-router-dom';
import { useVideoHealth, useCheckVideoHealth } from '@/api/admin';

const STATUS_BADGE: Record<string, string> = {
  ok: 'bg-success-100 text-success-700',
  dead: 'bg-danger-100 text-danger-700',
  unknown: 'bg-accent-100 text-accent-700',
};

function badge(status: string | null) {
  const key = status ?? 'unchecked';
  const cls = status ? STATUS_BADGE[status] ?? 'bg-muted text-muted-foreground' : 'bg-muted text-muted-foreground';
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${cls}`}>{key}</span>;
}

export default function VideoHealthList() {
  const { data, isLoading, isError } = useVideoHealth();
  const check = useCheckVideoHealth();

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-ink">Video health</h1>
        <button
          type="button"
          onClick={() => check.mutate()}
          disabled={check.isPending}
          className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {check.isPending ? 'Checking…' : 'Check now'}
        </button>
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {isError && <p className="text-danger-500">Failed to load video health.</p>}

      {data && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left text-muted-foreground">
              <th className="py-2 pr-4">Module</th>
              <th className="py-2 pr-4">Lesson</th>
              <th className="py-2 pr-4">YouTube ID</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Checked</th>
              <th className="py-2 pr-4">Edit</th>
            </tr>
          </thead>
          <tbody>
            {data.map((v) => (
              <tr key={v.lesson_id} className="border-b border-line">
                <td className="py-2 pr-4 text-ink">{v.module_title}</td>
                <td className="py-2 pr-4 text-ink">{v.lesson_title}</td>
                <td className="py-2 pr-4 font-mono text-muted-foreground">{v.youtube_id || '∅'}</td>
                <td className="py-2 pr-4">{badge(v.status)}</td>
                <td className="py-2 pr-4 text-muted-foreground">
                  {v.checked_at ? new Date(v.checked_at).toLocaleDateString() : '—'}
                </td>
                <td className="py-2 pr-4">
                  <Link to={`/admin/modules/${v.module_id}`} className="text-brand-700 hover:underline">Edit</Link>
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td colSpan={6} className="py-4 text-muted-foreground">No video lessons.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
