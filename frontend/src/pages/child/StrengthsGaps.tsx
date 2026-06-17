import { useTranslation } from 'react-i18next';
import { useStrengths, type TopicStrength } from '@/api/ai';

const STATUS_STYLES: Record<string, { border: string; text: string; label: string; emoji: string }> = {
  strong: { border: 'border-l-success-500', text: 'text-success-700', label: 'Strong — keep it up!', emoji: '⭐' },
  needs_practice: { border: 'border-l-accent-400', text: 'text-accent-700', label: 'Needs practice', emoji: '🔄' },
  new: { border: 'border-l-brand-200', text: 'text-muted-foreground', label: 'Not started yet', emoji: '🆕' },
};

function MasteryRing({ value }: { value: number }) {
  const { t } = useTranslation('child');
  const pct = Math.round(value * 100);
  const circumference = 2 * Math.PI * 52;
  const offset = circumference - (value * circumference);

  return (
    <div className="flex flex-col items-center" role="img" aria-label={t('strengths.overallMasteryAriaLabel', { pct })}>
      <div className="relative h-[120px] w-[120px]">
        <svg viewBox="0 0 120 120" className="-rotate-90">
          <circle cx="60" cy="60" r="52" fill="none" stroke="#bae6fd" strokeWidth="10" />
          <circle
            cx="60" cy="60" r="52" fill="none" stroke="#7c3aed" strokeWidth="10"
            strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-gray-900">
          {pct}%
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold text-brand-600">{t('strengths.overallMastery')}</p>
      <p className="text-xs text-muted-foreground">{t('strengths.overallMasterySubtitle')}</p>
    </div>
  );
}

function TopicCard({ topic }: { topic: TopicStrength }) {
  const { t } = useTranslation('child');
  const style = STATUS_STYLES[topic.status] ?? STATUS_STYLES.new;
  const pct = Math.round(topic.mastery_score * 100);

  return (
    <div className={`rounded-xl border border-brand-100 ${style.border} border-l-4 bg-card p-4 shadow-sm`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold text-gray-900 text-sm">{topic.topic.replace(/_/g, ' ')}</p>
          <p className={`${style.text} text-xs mt-0.5`}>{style.emoji} {style.label}</p>
        </div>
        {topic.status !== 'new' ? (
          <span className={`${style.text} text-xl font-bold`}>{pct}%</span>
        ) : (
          <span className="text-xl font-bold text-muted-foreground">—</span>
        )}
      </div>

      {topic.status !== 'new' && (
        <div
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${topic.topic.replace(/_/g, ' ')} mastery: ${pct}%`}
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-brand-100"
        >
          <div
            className={`h-full rounded-full ${topic.status === 'strong' ? 'bg-success-500' : 'bg-accent-400'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
        {topic.status !== 'new' && (
          <>
            <span>{t(topic.weak_count !== 1 ? 'strengths.weakConceptsPlural' : 'strengths.weakConcepts', { count: topic.weak_count })}</span>
            {topic.due_for_review > 0 && (
              <span className="text-accent-700">{t('strengths.dueForReview', { count: topic.due_for_review })}</span>
            )}
          </>
        )}
        {topic.status === 'new' && <span>{t('strengths.startToTrack')}</span>}
      </div>
    </div>
  );
}

export default function StrengthsGaps() {
  const { t } = useTranslation('child');
  const { data, isLoading } = useStrengths();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <p className="text-sm text-gray-500">{t('strengths.loading')}</p>
      </div>
    );
  }

  const topics = data?.topics ?? [];
  const overall = data?.overall_mastery ?? 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-extrabold text-gray-900">{t('strengths.pageTitle')}</h1>
      <p className="mt-1 text-sm text-gray-500">{t('strengths.subtitle')}</p>

      <div className="mt-6">
        <MasteryRing value={overall} />
      </div>

      <div className="mt-6 flex flex-col gap-3">
        {topics.length > 0 ? (
          topics.map((t) => <TopicCard key={t.topic} topic={t} />)
        ) : (
          <p className="text-sm text-center text-gray-500">
            {t('strengths.empty')}
          </p>
        )}
      </div>
    </div>
  );
}
