import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { parentApi, type MasteryReportChild } from '@/api/parent';
import { ParentZoneHeading } from '@/components/parent/ParentSection';

/**
 * The evidence hero (M6): what the household actually mastered this month,
 * rendered from W3 learning-objective + standards data. This card IS the
 * paid product's story — outcome proof, not feature lists.
 */
export function MasteryReportCard() {
  const { t } = useTranslation('parent');
  const { data, isLoading, isError } = useQuery({
    queryKey: ['mastery-report'],
    queryFn: parentApi.getMasteryReport,
  });

  if (isLoading) {
    return (
      <section aria-label={t('masteryReport.sectionAriaLabel')}>
        <ParentZoneHeading>{t('zones.thisMonth')}</ParentZoneHeading>
        <div className="rounded-2xl border border-brand-200 bg-white p-4 sm:p-6">
          <div className="h-5 w-2/3 animate-pulse rounded bg-brand-100" aria-hidden="true" />
          <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-brand-100" aria-hidden="true" />
        </div>
      </section>
    );
  }
  if (isError || !data || !Array.isArray(data.children)) return null;

  const kids = data.children;
  if (kids.length === 0) return null;

  const total = data.household_mastered_count;
  let headline: string;
  if (kids.length === 1) {
    if (total > 0) {
      headline = total === 1
        ? t('masteryReport.singleChildSkills', { username: kids[0].username, count: total })
        : t('masteryReport.singleChildSkillsPlural', { username: kids[0].username, count: total });
    } else {
      headline = t('masteryReport.singleChildReport', { username: kids[0].username });
    }
  } else {
    if (total > 0) {
      headline = total === 1
        ? t('masteryReport.householdSkills', { count: total, days: data.window_days })
        : t('masteryReport.householdSkillsPlural', { count: total, days: data.window_days });
    } else {
      headline = t('masteryReport.householdReport');
    }
  }

  return (
    <section aria-label={t('masteryReport.sectionAriaLabel')}>
      <ParentZoneHeading>{t('zones.thisMonth')}</ParentZoneHeading>
      <div className="rounded-2xl border border-brand-200 bg-white p-4 sm:p-6">
        <h2 className="text-base font-extrabold text-brand-900">{headline}</h2>
        <div className="mt-3 space-y-4">
          {kids.map((child) => (
            <ChildMastery key={child.user_id} child={child} multi={kids.length > 1} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ChildMastery({ child, multi }: { child: MasteryReportChild; multi: boolean }) {
  const { t } = useTranslation('parent');
  const next = child.next_recommendation;
  const nextLabel = next?.module_title
    ? next.level_title
      ? `${next.module_title} — ${next.level_title}`
      : next.module_title
    : null;

  return (
    <div>
      {multi && (
        <p className="text-sm font-bold text-ink">
          {t('masteryReport.multiChildStats', { username: child.username, count: child.mastered_count, total: child.mastered_total })}
        </p>
      )}
      {child.objectives.length > 0 ? (
        <ul className="mt-1.5 flex flex-wrap gap-1.5" aria-label={t('masteryReport.skillsAriaLabel', { username: child.username })}>
          {child.objectives.map((obj) => (
            <li
              key={obj}
              className="rounded-full bg-success-50 px-2.5 py-1 text-xs font-semibold text-success-700"
            >
              {/* eslint-disable-next-line i18next/no-literal-string -- decorative check glyph */}
              <span aria-hidden="true">✓ </span>{t('masteryReport.canNow', { objective: obj })}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-sm text-muted-foreground">
          {nextLabel
            ? t('masteryReport.noMasteriesQueued', { nextLabel })
            : t('masteryReport.noMasteriesNone')}
        </p>
      )}
      {child.standards.length > 0 && (
        <p className="mt-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('masteryReport.alignedTo', { frameworks: Array.from(new Set(child.standards.map((s) => s.framework).filter(Boolean))).join(' · ') })}
        </p>
      )}
      {child.weak_topic && nextLabel && (
        <p className="mt-1.5 text-sm text-muted-foreground">
          {t('masteryReport.worthALook', { topic: child.weak_topic.replace(/_/g, ' '), nextLabel })}
        </p>
      )}
    </div>
  );
}
