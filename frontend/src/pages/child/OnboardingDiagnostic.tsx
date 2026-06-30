import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { OptionCard } from '@/components/child/ui/OptionCard';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { useAgeTier } from '@/lib/ageTier';
import {
  startDiagnostic,
  submitDiagnostic,
  type DiagnosticKind,
  type DiagnosticSessionItem,
  type DiagnosticTopicResult,
} from '@/api/diagnostic';

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

type Props = {
  kind?: DiagnosticKind;
  onComplete: () => void;
};

type Phase =
  | { kind: 'loading' }
  | { kind: 'quiz'; sessionId: string; items: DiagnosticSessionItem[]; idx: number; answers: Record<string, number> }
  | { kind: 'results'; topics: DiagnosticTopicResult[] }
  | { kind: 'done' };

export default function OnboardingDiagnostic({ kind = 'baseline', onComplete }: Props) {
  const { t } = useTranslation('diagnostic');
  const tier = useAgeTier();

  const [phase, setPhase] = useState<Phase>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;

    startDiagnostic(kind)
      .then(async (session) => {
        if (cancelled) return;
        if (!session) {
          // Null response treated as error — fall through to home
          onComplete();
          return;
        }
        if (session.items.length === 0) {
          // Empty bank — auto-skip
          try {
            await submitDiagnostic({ session_id: session.session_id, skipped: true });
          } catch (err) {
            console.error('[diagnostic] auto-skip submit failed', err);
          }
          if (!cancelled) onComplete();
          return;
        }
        if (!cancelled) {
          setPhase({ kind: 'quiz', sessionId: session.session_id, items: session.items, idx: 0, answers: {} });
        }
      })
      .catch((err) => {
        console.error('[diagnostic] start failed', err);
        if (!cancelled) onComplete();
      });

    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  async function handleSkip(sessionId: string) {
    try {
      await submitDiagnostic({ session_id: sessionId, skipped: true });
    } catch (err) {
      console.error('[diagnostic] skip submit failed', err);
    }
    onComplete();
  }

  async function handleFinish(sessionId: string, answers: Record<string, number>) {
    try {
      const result = await submitDiagnostic({ session_id: sessionId, answers });
      if (result && result.topics.length > 0) {
        setPhase({ kind: 'results', topics: result.topics });
        return;
      }
    } catch (err) {
      console.error('[diagnostic] submit failed', err);
    }
    onComplete();
  }

  // ── Loading ─────────────────────────────────────────────────────
  if (phase.kind === 'loading') {
    return (
      <div className="mx-auto max-w-xl px-4 py-10 text-center">
        <p className="text-sm text-muted-foreground" role="status" aria-live="polite">
          {t('loading')}
        </p>
      </div>
    );
  }

  // ── Results ─────────────────────────────────────────────────────
  if (phase.kind === 'results') {
    const isProgress = kind === 'progress';
    const headingKey = isProgress
      ? (tier === 'investor' ? 'results.progress_heading_investor' : 'results.progress_heading_explorer')
      : (tier === 'investor' ? 'results.heading_investor' : 'results.heading_explorer');
    const subKey = isProgress
      ? (tier === 'investor' ? 'results.progress_subInvestor' : 'results.progress_subExplorer')
      : (tier === 'investor' ? 'results.subInvestor' : 'results.subExplorer');
    const ctaKey = isProgress ? 'results.progress_cta' : 'results.cta';
    return (
      <div className="mx-auto max-w-xl px-4 py-10">
        <div className="rounded-3xl bg-white p-6 shadow-lg shadow-brand-600/10 text-center space-y-4">
          <h1 className="text-xl font-extrabold text-ink">{t(headingKey)}</h1>
          <p className="text-sm text-muted-foreground">{t(subKey)}</p>
          <div
            className="flex flex-wrap justify-center gap-2 pt-2"
            role="list"
            aria-label={t(headingKey)}
          >
            {phase.topics.map((topic) => (
              <span
                key={topic.topic}
                role="listitem"
                aria-label={t('results.topicChipAriaLabel', { topic: topic.topic })}
                className="inline-flex items-center rounded-full bg-brand-100 px-3 py-1 text-sm font-semibold text-brand-700 capitalize"
              >
                {topic.topic}
              </span>
            ))}
          </div>
          <GradientButton full onClick={onComplete}>
            {t(ctaKey)}
          </GradientButton>
        </div>
      </div>
    );
  }

  // ── Quiz ─────────────────────────────────────────────────────────
  if (phase.kind === 'quiz') {
    const { sessionId, items, idx, answers } = phase;
    const item = items[idx];
    const selected = answers[item.id] ?? null;
    const isLast = idx === items.length - 1;

    function selectAnswer(choiceIdx: number) {
      setPhase({
        kind: 'quiz',
        sessionId,
        items,
        idx,
        answers: { ...answers, [item.id]: choiceIdx },
      });
    }

    function goNext() {
      if (isLast) {
        void handleFinish(sessionId, { ...answers });
      } else {
        setPhase({ kind: 'quiz', sessionId, items, idx: idx + 1, answers });
      }
    }

    const isProgress = kind === 'progress';

    return (
      <div className="mx-auto max-w-xl px-4 py-6 space-y-4">
        {/* Intro framing — shown on the first question so the child understands
            this is a no-pressure baseline, not a graded test */}
        {idx === 0 && (
          <div className="rounded-3xl bg-brand-50 p-4 text-center">
            <h1 className="text-base font-extrabold text-ink">
              {t(isProgress ? 'quiz.introTitle_progress' : 'quiz.introTitle')}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {t(isProgress ? 'quiz.introBody_progress' : 'quiz.introBody')}
            </p>
          </div>
        )}

        {/* Progress */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span aria-live="polite">
            {t('quiz.progress', { current: idx + 1, total: items.length })}
          </span>
          <button
            type="button"
            onClick={() => void handleSkip(sessionId)}
            className="text-sm font-semibold text-brand-700 underline hover:text-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded px-1 py-0.5 min-h-[44px] flex items-center"
          >
            {t('quiz.skip')}
          </button>
        </div>

        {/* Question card */}
        <div className="space-y-5 rounded-3xl bg-white p-6 shadow-lg shadow-brand-600/10">
          <p className="text-lg font-extrabold leading-snug text-ink">{item.question}</p>

          <div
            className="space-y-3"
            role="radiogroup"
            aria-label={t('quiz.answerChoicesLabel')}
          >
            {item.choices.map((choice, i) => (
              <OptionCard
                key={i}
                letter={LETTERS[i] ?? '?'}
                state={selected === i ? 'selected' : 'default'}
                checked={selected === i}
                onSelect={() => selectAnswer(i)}
              >
                {choice}
              </OptionCard>
            ))}
          </div>

          <GradientButton
            full
            disabled={selected === null}
            onClick={goNext}
          >
            {isLast ? t('quiz.finish') : t('quiz.next')}
          </GradientButton>
        </div>
      </div>
    );
  }

  return null;
}
