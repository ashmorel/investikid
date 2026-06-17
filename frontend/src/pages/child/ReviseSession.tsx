import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { reviseApi, type ReviseQuestion, type ReviseAnswerResult } from '@/api/revise';
import { OptionCard, type OptionState } from '@/components/child/ui/OptionCard';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { FeedbackPanel } from '@/components/child/ui/FeedbackPanel';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';
import { useTranslation } from 'react-i18next';

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

export default function ReviseSession() {
  const { t } = useTranslation('revise');
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const moduleId = params.get('module') ?? undefined;

  const [items, setItems] = useState<ReviseQuestion[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [result, setResult] = useState<ReviseAnswerResult | null>(null);
  const [correctCount, setCorrectCount] = useState(0);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // On a network error, degrade to the terminal "all caught up" state rather
    // than spinning on "Loading…" forever.
    reviseApi
      .getSession(moduleId)
      .then((s) => setItems(s?.items ?? []))
      .catch(() => setItems([]));
  }, [moduleId]);

  if (items === null) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <p className="text-sm text-muted-foreground">{t('session.loading')}</p>
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 text-center">
        <p className="text-lg font-semibold">{t('session.empty.heading')}</p>
        <p className="mt-1 text-sm text-muted-foreground">{t('session.empty.sub')}</p>
        <GradientButton full className="mt-4" onClick={() => navigate('/home')}>
          {t('session.empty.backHome')}
        </GradientButton>
      </div>
    );
  }
  if (done) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 text-center">
        <p className="text-lg font-semibold">{t('session.done.heading')}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {t('session.done.score', { correct: correctCount, total: items.length })}
        </p>
        <GradientButton full className="mt-4" onClick={() => navigate('/home')}>
          {t('session.done.cta')}
        </GradientButton>
      </div>
    );
  }

  const list = items;
  const q = list[idx];

  function optionState(i: number): OptionState {
    if (!result) return selected === i ? 'selected' : 'default';
    if (i === result.answer_index) return 'correct';
    if (i === selected) return 'incorrect';
    return 'default';
  }

  async function handleCheck() {
    if (selected === null || submitting || result) return;
    setSubmitting(true);
    try {
      const r = await reviseApi.postAnswer(q.ref, selected);
      if (!r) return;
      playSound(r.correct ? 'correct' : 'wrong');
      void haptic(r.correct ? 'success' : 'warning');
      setResult(r);
      if (r.correct) setCorrectCount((c) => c + 1);
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    setResult(null);
    setSelected(null);
    if (idx + 1 >= list.length) setDone(true);
    else setIdx((n) => n + 1);
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-3 flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {t('session.progress', { current: idx + 1, total: items.length })}
        </span>
        <span
          className={
            q.kind === 'weak'
              ? 'rounded-full bg-danger-100 px-2 py-0.5 font-semibold text-danger-700'
              : 'rounded-full bg-brand-100 px-2 py-0.5 font-semibold text-brand-700'
          }
        >
          {q.kind === 'weak' ? t('session.kindBadge.weak') : t('session.kindBadge.normal')}
        </span>
      </div>

      <div className="space-y-5 rounded-3xl bg-white p-6 shadow-lg shadow-brand-600/10">
        <p className="text-lg font-extrabold leading-snug text-gray-900">{q.question}</p>

        <div className="space-y-3" role="radiogroup" aria-label={t('session.answerChoicesLabel')}>
          {q.choices.map((choice, i) => (
            <OptionCard
              key={i}
              letter={LETTERS[i] ?? '?'}
              state={optionState(i)}
              checked={selected === i}
              disabled={!!result || submitting}
              onSelect={() => setSelected(i)}
            >
              {choice}
            </OptionCard>
          ))}
        </div>

        <div aria-live="polite">
          {result ? (
            <>
              <FeedbackPanel
                correct={result.correct}
                explanation={result.explanation}
                correctAnswer={!result.correct ? q.choices[result.answer_index] : undefined}
              />
              {(result.xp_awarded > 0 || result.goal_met) && (
                <p className="mt-2 text-center text-sm font-bold text-brand-700">
                  {result.xp_awarded > 0 && <span>{t('session.xpAwarded', { xp: result.xp_awarded })}</span>}
                  {result.goal_met && <span>{t('session.streakKept')}</span>}
                </p>
              )}
              <GradientButton full className="mt-3" onClick={next}>
                {idx + 1 >= items.length ? t('session.finish') : t('session.next')}
              </GradientButton>
            </>
          ) : (
            <GradientButton
              full
              disabled={selected === null || submitting}
              onClick={handleCheck}
            >
              {t('session.checkAnswer')}
            </GradientButton>
          )}
        </div>
      </div>
    </div>
  );
}
