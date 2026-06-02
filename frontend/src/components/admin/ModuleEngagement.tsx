import { useModuleEngagement } from '@/api/admin';
import type { LessonEngagement } from '@/api/admin';

function pct(v: number | null): string {
  return v == null ? '—' : `${Math.round(v * 100)}%`;
}
function score(v: number | null): string {
  return v == null ? '—' : `${Math.round(v * 100)}%`;
}

export default function ModuleEngagement({ moduleId }: { moduleId: string }) {
  const { data, isLoading, isError } = useModuleEngagement(moduleId);

  if (isLoading) return <p className="text-slate-400">Loading engagement…</p>;
  if (isError || !data) return <p className="text-slate-400">Engagement data unavailable.</p>;
  if (data.learners_started === 0) {
    return <p className="text-slate-400">No engagement data yet — no learners have started this module.</p>;
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
      <h3 id="engagement-heading" className="mb-3 text-lg font-semibold text-slate-50">Engagement</h3>

      <dl className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-400">Learners started</dt>
          <dd className="text-xl font-semibold text-slate-50">{data.learners_started}</dd>
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-400">Completed module</dt>
          <dd className="text-xl font-semibold text-slate-50">{pct(data.completion_rate)}</dd>
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-400">Avg score</dt>
          <dd className="text-xl font-semibold text-slate-50">{score(data.average_score)}</dd>
        </div>
      </dl>

      <table className="w-full text-left text-sm">
        <caption className="sr-only">Per-lesson engagement for this module</caption>
        <thead className="text-xs text-slate-400">
          <tr>
            <th scope="col" className="py-1 pr-2">Lesson</th>
            <th scope="col" className="py-1 pr-2">Views</th>
            <th scope="col" className="py-1 pr-2">Completed</th>
            <th scope="col" className="py-1 pr-2">Rate</th>
            <th scope="col" className="py-1 pr-2">Avg score</th>
            <th scope="col" className="py-1 pr-2">Drop-off</th>
          </tr>
        </thead>
        <tbody>
          {data.lessons.map((l) => (
            <tr key={l.lesson_id} className={l.lesson_id === worst ? 'bg-amber-500/10' : ''}>
              <td className="py-1 pr-2 text-slate-50">{l.label}</td>
              <td className="py-1 pr-2 text-slate-300">{l.views}</td>
              <td className="py-1 pr-2 text-slate-300">{l.completions}</td>
              <td className="py-1 pr-2 text-slate-300">{pct(l.completion_rate)}</td>
              <td className="py-1 pr-2 text-slate-300">{l.type === 'quiz' || l.type === 'scenario' ? score(l.average_score) : '—'}</td>
              <td className="py-1 pr-2 text-slate-300">{l.drop_off > 0 ? `−${l.drop_off}` : '0'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
