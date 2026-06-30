import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useStrengths, type TopicStrength, type ConceptStrength } from '@/api/ai';

type Filter = 'all' | 'needs_practice' | 'strong' | 'new';

// Status presentation. Labels/emoji stay here (English, matching the rest of
// this surface); all other copy is translated via t().
const STATUS: Record<
  TopicStrength['status'],
  { emoji: string; label: string; pill: string; text: string; bar: string; accent: string }
> = {
  strong: {
    emoji: '⭐', label: 'Strong — keep it up!',
    pill: 'bg-success-100 text-success-700', text: 'text-success-700',
    bar: 'bg-success-500', accent: 'bg-success-500',
  },
  needs_practice: {
    emoji: '🔄', label: 'Needs practice',
    pill: 'bg-accent-100 text-accent-700', text: 'text-accent-700',
    bar: 'bg-accent-400', accent: 'bg-accent-400',
  },
  new: {
    emoji: '🆕', label: 'Not started yet',
    pill: 'bg-brand-100 text-muted-foreground', text: 'text-muted-foreground',
    bar: '', accent: 'bg-brand-200',
  },
};

// Most-actionable first: practice → strong → not started.
const SORT_ORDER: Record<TopicStrength['status'], number> = { needs_practice: 0, strong: 1, new: 2 };

const FILTERS: { key: Filter; labelKey: string }[] = [
  { key: 'all', labelKey: 'strengths.filterAll' },
  { key: 'needs_practice', labelKey: 'strengths.filterNeedsPractice' },
  { key: 'strong', labelKey: 'strengths.filterStrong' },
  { key: 'new', labelKey: 'strengths.filterNew' },
];

function MasteryRing({ value }: { value: number }) {
  const { t } = useTranslation('child');
  const pct = Math.round(value * 100);
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - value * circumference;
  return (
    <div
      className="relative h-24 w-24 shrink-0"
      role="img"
      aria-label={t('strengths.overallMasteryAriaLabel', { pct })}
    >
      <svg viewBox="0 0 96 96" className="-rotate-90">
        <circle cx="48" cy="48" r="40" fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="9" />
        <circle
          cx="48" cy="48" r="40" fill="none" stroke="#ffffff" strokeWidth="9"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xl font-extrabold text-white">
        {pct}%
      </span>
    </div>
  );
}

function ConceptPill({ concept }: { concept: ConceptStrength }) {
  const s = STATUS[concept.status] ?? STATUS.new;
  return (
    <div className="flex items-center justify-between gap-2 py-1">
      <span className="text-sm text-ink">{concept.name}</span>
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-bold ${s.pill}`}>
        {s.emoji} {s.label}
      </span>
    </div>
  );
}

function TopicCard({ topic }: { topic: TopicStrength }) {
  const { t } = useTranslation('child');
  const s = STATUS[topic.status] ?? STATUS.new;
  const pct = Math.round(topic.mastery_score * 100);
  const isNew = topic.status === 'new';
  const name = topic.topic.replace(/_/g, ' ');
  const hasConcepts = (topic.concepts ?? []).length > 0;
  const [open, setOpen] = useState(false);
  const drilldownId = `concepts-${topic.topic}`;

  return (
    <div className="flex overflow-hidden rounded-2xl border border-brand-200 bg-card shadow-sm">
      <div className={`w-1.5 shrink-0 ${s.accent}`} aria-hidden="true" />
      <div className="min-w-0 flex-1 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-ink">{name}</p>
            <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-bold ${s.pill}`}>
              {s.emoji} {s.label}
            </span>
          </div>
          <span className={`shrink-0 text-xl font-extrabold ${isNew ? 'text-muted-foreground' : s.text}`}>
            {isNew ? '—' : `${pct}%`}
          </span>
        </div>

        {!isNew && (
          <div
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${name} mastery: ${pct}%`}
            className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-brand-100"
          >
            <div className={`h-full rounded-full ${s.bar}`} style={{ width: `${pct}%` }} />
          </div>
        )}

        <div className="mt-2.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {isNew ? (
            <span>{t('strengths.startToTrack')}</span>
          ) : (
            <>
              <span>
                {t(topic.weak_count !== 1 ? 'strengths.weakConceptsPlural' : 'strengths.weakConcepts', {
                  count: topic.weak_count,
                })}
              </span>
              {topic.due_for_review > 0 && (
                <span className="text-accent-700">{t('strengths.dueForReview', { count: topic.due_for_review })}</span>
              )}
            </>
          )}
        </div>

        {hasConcepts && (
          <div className="mt-3">
            <button
              type="button"
              aria-expanded={open}
              aria-controls={drilldownId}
              onClick={() => setOpen((v) => !v)}
              className="flex min-h-[44px] w-full items-center justify-between gap-2 rounded-lg px-2 text-xs font-bold text-brand-700 hover:bg-brand-50"
            >
              <span>{t('strengths.conceptsSection')}</span>
              <span aria-hidden="true">{open ? '▲' : '▼'}</span>
              <span className="sr-only">
                {open ? t('strengths.collapseConcepts') : t('strengths.expandConcepts')}
              </span>
            </button>
            {open && (
              <div id={drilldownId} className="mt-1 divide-y divide-brand-100 px-2">
                {(topic.concepts ?? []).map((c) => (
                  <ConceptPill key={c.concept_id} concept={c} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function StrengthsGaps() {
  const { t } = useTranslation('child');
  const { data, isLoading } = useStrengths();
  const [filter, setFilter] = useState<Filter>('all');

  const topics = useMemo(() => data?.topics ?? [], [data]);
  const overall = data?.overall_mastery ?? 0;

  const strongCount = topics.filter((x) => x.status === 'strong').length;
  const practiceCount = topics.filter((x) => x.status === 'needs_practice').length;
  const dueTotal = topics.reduce((n, x) => n + x.due_for_review, 0);

  const heroHeadline =
    overall >= 0.7 ? t('strengths.heroHigh') : overall >= 0.4 ? t('strengths.heroMid') : t('strengths.heroLow');

  const sorted = useMemo(
    () =>
      [...topics].sort(
        (a, b) => SORT_ORDER[a.status] - SORT_ORDER[b.status] || a.mastery_score - b.mastery_score,
      ),
    [topics],
  );
  const shown = filter === 'all' ? sorted : sorted.filter((x) => x.status === filter);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <p className="text-sm text-muted-foreground">{t('strengths.loading')}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-4 py-4 sm:px-6 sm:py-6">
      <header>
        <h1 className="text-2xl font-extrabold text-ink">{t('strengths.pageTitle')}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t('strengths.subtitle')}</p>
      </header>

      {/* Mastery hero */}
      <section className="rounded-2xl bg-brand-gradient p-4 text-white sm:p-5" aria-label={t('strengths.overallMastery')}>
        <div className="flex items-center gap-4">
          <MasteryRing value={overall} />
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-wider text-white/85">{t('strengths.overallMastery')}</p>
            <p className="text-lg font-extrabold">{heroHeadline}</p>
            <p className="text-sm text-white/90">
              {t('strengths.summary', { strong: strongCount, practice: practiceCount })}
            </p>
            {dueTotal > 0 && (
              <Link
                to="/revise"
                className="mt-2 inline-flex items-center gap-1 rounded-full bg-white px-3 py-1.5 text-xs font-bold text-brand-700"
              >
                {t('strengths.dueCta', { count: dueTotal })} <span aria-hidden="true">→</span>
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* Topics */}
      <section className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t('strengths.topicsZone')}</h2>

        <div className="flex flex-wrap gap-2" role="group" aria-label={t('strengths.topicsZone')}>
          {FILTERS.map((f) => {
            const active = filter === f.key;
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                aria-pressed={active}
                className={`min-h-[36px] rounded-full px-3 py-1.5 text-xs font-bold ${
                  active ? 'bg-brand-600 text-white' : 'border border-brand-200 bg-card text-ink'
                }`}
              >
                {t(f.labelKey)}
              </button>
            );
          })}
        </div>

        {shown.length > 0 ? (
          <div className="flex flex-col gap-3">
            {shown.map((topic) => (
              <TopicCard key={topic.topic} topic={topic} />
            ))}
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-muted-foreground">{t('strengths.empty')}</p>
        )}
      </section>
    </div>
  );
}
