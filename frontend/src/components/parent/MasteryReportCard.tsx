import { useQuery } from '@tanstack/react-query';
import { parentApi, type MasteryReportChild } from '@/api/parent';

/**
 * The evidence hero (M6): what the household actually mastered this month,
 * rendered from W3 learning-objective + standards data. This card IS the
 * paid product's story — outcome proof, not feature lists.
 */
export function MasteryReportCard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['mastery-report'],
    queryFn: parentApi.getMasteryReport,
  });

  if (isLoading) {
    return (
      <section aria-label="Mastery report" className="mb-4 rounded-2xl border border-brand-200 bg-white p-4 sm:p-6">
        <div className="h-5 w-2/3 animate-pulse rounded bg-brand-100" aria-hidden="true" />
        <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-brand-100" aria-hidden="true" />
      </section>
    );
  }
  if (isError || !data) return null;

  const kids = data.children;
  if (kids.length === 0) return null;

  const total = data.household_mastered_count;
  const headline =
    kids.length === 1
      ? total > 0
        ? `${kids[0].username} mastered ${total} skill${total === 1 ? '' : 's'} this month`
        : `${kids[0].username}'s learning report`
      : total > 0
        ? `${total} skill${total === 1 ? '' : 's'} mastered in the last ${data.window_days} days`
        : 'Your family learning report';

  return (
    <section aria-label="Mastery report" className="mb-4 rounded-2xl border border-brand-200 bg-white p-4 sm:p-6">
      <h2 className="text-base font-extrabold text-brand-900">{headline}</h2>
      <div className="mt-3 space-y-4">
        {kids.map((child) => (
          <ChildMastery key={child.user_id} child={child} multi={kids.length > 1} />
        ))}
      </div>
    </section>
  );
}

function ChildMastery({ child, multi }: { child: MasteryReportChild; multi: boolean }) {
  const next = child.next_recommendation;
  const nextLabel = next?.module_title
    ? next.level_title
      ? `${next.module_title} — ${next.level_title}`
      : next.module_title
    : null;

  return (
    <div>
      {multi && (
        <p className="text-sm font-bold text-gray-800">
          {child.username} · {child.mastered_count} this month ({child.mastered_total} all-time)
        </p>
      )}
      {child.objectives.length > 0 ? (
        <ul className="mt-1.5 flex flex-wrap gap-1.5" aria-label={`Skills ${child.username} can now use`}>
          {child.objectives.map((obj) => (
            <li
              key={obj}
              className="rounded-full bg-success-50 px-2.5 py-1 text-xs font-semibold text-success-700"
            >
              <span aria-hidden="true">✓ </span>can now: {obj}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-sm text-gray-600">
          No new masteries yet{nextLabel ? (
            <>
              {' '}— <strong>{nextLabel}</strong> is queued up.
            </>
          ) : (
            '.'
          )}
        </p>
      )}
      {child.standards.length > 0 && (
        <p className="mt-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
          Aligned to {Array.from(new Set(child.standards.map((s) => s.framework).filter(Boolean))).join(' · ')}
        </p>
      )}
      {child.weak_topic && nextLabel && (
        <p className="mt-1.5 text-sm text-gray-700">
          Worth a look: <strong className="capitalize">{child.weak_topic.replace(/_/g, ' ')}</strong> — try{' '}
          <strong>{nextLabel}</strong> together.
        </p>
      )}
    </div>
  );
}
