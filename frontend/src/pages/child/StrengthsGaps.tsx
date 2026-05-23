import { useStrengths, type TopicStrength } from '@/api/ai';

const STATUS_STYLES: Record<string, { border: string; text: string; label: string; emoji: string }> = {
  strong: { border: 'border-l-green-400', text: 'text-green-400', label: 'Strong — keep it up!', emoji: '⭐' },
  needs_practice: { border: 'border-l-amber-400', text: 'text-amber-400', label: 'Needs practice', emoji: '🔄' },
  new: { border: 'border-l-slate-500', text: 'text-slate-400', label: 'Not started yet', emoji: '🆕' },
};

function MasteryRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const circumference = 2 * Math.PI * 52;
  const offset = circumference - (value * circumference);

  return (
    <div className="flex flex-col items-center" role="img" aria-label={`Overall mastery: ${pct}%`}>
      <div className="relative h-[120px] w-[120px]">
        <svg viewBox="0 0 120 120" className="-rotate-90">
          <circle cx="60" cy="60" r="52" fill="none" stroke="#334155" strokeWidth="10" />
          <circle
            cx="60" cy="60" r="52" fill="none" stroke="#a78bfa" strokeWidth="10"
            strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-white">
          {pct}%
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold text-purple-400">Overall Mastery</p>
      <p className="text-xs text-slate-400">Across all topics you've studied</p>
    </div>
  );
}

function TopicCard({ topic }: { topic: TopicStrength }) {
  const style = STATUS_STYLES[topic.status] ?? STATUS_STYLES.new;
  const pct = Math.round(topic.mastery_score * 100);

  return (
    <div className={`rounded-xl border-l-4 ${style.border} bg-slate-800 p-4`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold text-white text-sm">{topic.topic.replace(/_/g, ' ')}</p>
          <p className={`${style.text} text-xs mt-0.5`}>{style.emoji} {style.label}</p>
        </div>
        {topic.status !== 'new' ? (
          <span className={`${style.text} text-xl font-bold`}>{pct}%</span>
        ) : (
          <span className="text-xl font-bold text-slate-500">—</span>
        )}
      </div>

      {topic.status !== 'new' && (
        <div
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${topic.topic.replace(/_/g, ' ')} mastery: ${pct}%`}
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-600"
        >
          <div
            className={`h-full rounded-full ${topic.status === 'strong' ? 'bg-green-400' : 'bg-amber-400'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      <div className="flex gap-4 mt-2 text-xs text-slate-400">
        {topic.status !== 'new' && (
          <>
            <span>{topic.weak_count} weak concept{topic.weak_count !== 1 ? 's' : ''}</span>
            {topic.due_for_review > 0 && (
              <span className="text-amber-400">{topic.due_for_review} due for review</span>
            )}
          </>
        )}
        {topic.status === 'new' && <span>Start this topic to track your progress</span>}
      </div>
    </div>
  );
}

export default function StrengthsGaps() {
  const { data, isLoading } = useStrengths();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <p className="text-sm text-gray-500">Loading your progress…</p>
      </div>
    );
  }

  const topics = data?.topics ?? [];
  const overall = data?.overall_mastery ?? 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-extrabold text-gray-900">My Progress</h1>
      <p className="mt-1 text-sm text-gray-500">See how you're doing across all topics</p>

      <div className="mt-6">
        <MasteryRing value={overall} />
      </div>

      <div className="mt-6 flex flex-col gap-3">
        {topics.length > 0 ? (
          topics.map((t) => <TopicCard key={t.topic} topic={t} />)
        ) : (
          <p className="text-sm text-center text-gray-500">
            Complete some lessons to see your progress here!
          </p>
        )}
      </div>
    </div>
  );
}
