import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { reviseApi, type ReviseQuestion, type ReviseAnswerResult } from '@/api/revise';
import { Button } from '@/components/ui/button';

export default function ReviseSession() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const moduleId = params.get('module') ?? undefined;

  const [items, setItems] = useState<ReviseQuestion[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [result, setResult] = useState<ReviseAnswerResult | null>(null);
  const [correctCount, setCorrectCount] = useState(0);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    reviseApi.getSession(moduleId).then((s) => setItems(s?.items ?? []));
  }, [moduleId]);

  if (items === null) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 text-center">
        <p className="text-lg font-semibold">All caught up! 🎉</p>
        <p className="mt-1 text-sm text-muted-foreground">Nothing to revise right now.</p>
        <Button className="mt-4" onClick={() => navigate('/home')}>Back to home</Button>
      </div>
    );
  }
  if (done) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 text-center">
        <p className="text-lg font-semibold">Great revising! 🌟</p>
        <p className="mt-1 text-sm text-muted-foreground">{correctCount} / {items.length} correct</p>
        <Button className="mt-4" onClick={() => navigate('/home')}>Done</Button>
      </div>
    );
  }

  const list = items;
  const q = list[idx];

  async function choose(i: number) {
    if (submitting || result) return;
    setSubmitting(true);
    try {
      const r = await reviseApi.postAnswer(q.ref, i);
      if (!r) return;
      setResult(r);
      if (r.correct) setCorrectCount((c) => c + 1);
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    setResult(null);
    if (idx + 1 >= list.length) setDone(true);
    else setIdx((n) => n + 1);
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-2 flex items-center justify-between text-sm text-muted-foreground">
        <span>{idx + 1} of {items.length}</span>
        <span className={q.kind === 'weak'
          ? 'rounded-full bg-danger-100 px-2 py-0.5 font-semibold text-danger-700'
          : 'rounded-full bg-brand-100 px-2 py-0.5 font-semibold text-brand-700'}>
          {q.kind === 'weak' ? 'Needs practice' : 'Quick refresher'}
        </span>
      </div>
      <h1 className="text-xl font-semibold">{q.question}</h1>
      <div className="mt-4 flex flex-col gap-2">
        {q.choices.map((c, i) => {
          const isAnswer = result && i === result.answer_index;
          const isChosenWrong = result && !result.correct && i !== result.answer_index;
          return (
            <Button
              key={i}
              variant="outline"
              disabled={!!result || submitting}
              onClick={() => choose(i)}
              className={[
                'justify-start text-left min-h-[44px]',
                isAnswer ? 'border-success-500 bg-success-50' : '',
                isChosenWrong ? 'opacity-60' : '',
              ].join(' ')}
            >
              {c}
            </Button>
          );
        })}
      </div>
      <div aria-live="polite" className="mt-4">
        {result && (
          <div className="rounded-xl border border-brand-100 bg-brand-50 p-3">
            <p className="font-semibold">{result.correct ? 'Correct! ' : 'Not quite. '}
              {result.xp_awarded > 0 && <span>+{result.xp_awarded} XP</span>}
              {result.goal_met && <span> · 🔥 streak kept!</span>}
            </p>
            {result.explanation && <p className="mt-1 text-sm text-brand-800">{result.explanation}</p>}
            <Button className="mt-3" onClick={next}>
              {idx + 1 >= items.length ? 'Finish' : 'Next'}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
