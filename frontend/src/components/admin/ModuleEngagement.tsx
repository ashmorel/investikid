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

  if (isLoading) return <p className="text-muted-foreground">Loading engagement…</p>;
  if (isError || !data) return <p className="text-muted-foreground">Engagement data unavailable.</p>;
  if (data.learners_started === 0) {
    return <p className="text-muted-foreground">No engagement data yet — no learners have started this module.</p>;
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
      <h3 id="engagement-heading" className="mb-3 text-lg font-semibold text-ink">Engagement</h3>

      <dl className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-line bg-card p-3">
          <dt className="text-xs text-muted-foreground">Learners started</dt>
          <dd className="text-xl font-semibold text-ink">{data.learners_started}</dd>
        </div>
        <div className="rounded-md border border-line bg-card p-3">
          <dt className="text-xs text-muted-foreground">Completed module</dt>
          <dd className="text-xl font-semibold text-ink">{pct(data.completion_rate)}</dd>
        </div>
        <div className="rounded-md border border-line bg-card p-3">
          <dt className="text-xs text-muted-foreground">Avg score</dt>
          <dd className="text-xl font-semibold text-ink">{score(data.average_score)}</dd>
        </div>
      </dl>

      <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Per-lesson engagement for this module</caption>
        <thead className="text-xs text-muted-foreground">
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
