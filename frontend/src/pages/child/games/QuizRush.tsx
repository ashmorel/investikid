import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getQuizRushSession, submitQuizRushScore, type QuizItem, type QuizScoreResult } from '@/api/arcade';

const ROUND_SECONDS = 60;
const QUIZ_GRADIENT = { background: 'linear-gradient(135deg, #ea580c, #dc2626)' };
type Phase = 'idle' | 'playing' | 'done';

export default function QuizRush() {
  const { t } = useTranslation('arcade');
  const [phase, setPhase] = useState<Phase>('idle');
  const [items, setItems] = useState<QuizItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [combo, setCombo] = useState(0);
  const [seconds, setSeconds] = useState(ROUND_SECONDS);
  const answersRef = useRef<{ lesson_id: string; choice_index: number; time_ms: number }[]>([]);
  const itemsRef = useRef<QuizItem[]>([]);
  const [result, setResult] = useState<QuizScoreResult | null>(null);
  const finishedRef = useRef(false);

  const finish = useCallback(async () => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    setPhase('done');
    const res = await submitQuizRushScore({ session_items: itemsRef.current, answers: answersRef.current });
    if (res !== null) {
      setResult(res);
    }
  }, []);

  // Keep itemsRef in sync
  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  // Countdown: only ticks while playing, stops at 0
  useEffect(() => {
    if (phase !== 'playing') return;
    if (seconds <= 0) return;
    const id = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(id);
  }, [phase, seconds]);

  // When seconds reaches 0 and we're still playing, trigger finish
  useEffect(() => {
    if (phase === 'playing' && seconds <= 0) {
      void finish();
    }
  }, [phase, seconds, finish]);

  async function start() {
    finishedRef.current = false;
    const session = await getQuizRushSession();
    const newItems = session?.items ?? [];
    itemsRef.current = newItems;
    answersRef.current = [];
    setItems(newItems);
    setIdx(0);
    setCombo(0);
    setSeconds(ROUND_SECONDS);
    setResult(null);
    setPhase('playing');
  }

  function answer(choice: number) {
    const it = itemsRef.current[idx];
    if (!it) return;
    answersRef.current.push({ lesson_id: it.lesson_id, choice_index: choice, time_ms: 0 });
    setCombo((c) => (choice === it.answer_index ? c + 1 : 0));
    if (idx + 1 >= itemsRef.current.length) {
      void finish();
    } else {
      setIdx((i) => i + 1);
    }
  }

  if (phase === 'idle') {
    return (
      <main className="mx-auto max-w-md space-y-4 p-4">
        <div
          style={QUIZ_GRADIENT}
          className="flex flex-col items-center gap-2 rounded-3xl p-7 text-center text-white shadow-lg"
        >
          <span className="text-4xl" aria-hidden="true">&#9889;</span>
          <h1 className="text-2xl font-extrabold">{t('quizRush.name')}</h1>
          <p className="text-sm text-white/85">{t('quizRush.tagline')}</p>
          <button
            type="button"
            onClick={() => void start()}
            className="mt-2 min-h-[44px] rounded-xl bg-white px-8 py-2.5 font-extrabold text-amber-700 shadow-sm transition hover:bg-amber-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            {t('quizRush.start')}
          </button>
        </div>
        <Link
          to="/arcade"
          className="block min-h-[44px] py-2 text-center text-sm font-semibold text-brand-600 hover:underline focus-visible:outline focus-visible:outline-2"
        >
          {t('quizRush.backToArcade')}
        </Link>
      </main>
    );
  }

  if (phase === 'done') {
    return (
      <main className="mx-auto max-w-md space-y-4 p-4">
        <div className="flex flex-col items-center gap-3 rounded-3xl border border-amber-200 bg-amber-50 p-6 text-center">
          <h2 className="text-lg font-extrabold text-amber-700">
            <span aria-hidden="true">🎉 </span>{t('quizRush.results')}
          </h2>
          <p className="text-5xl font-extrabold text-amber-900">{result?.points ?? 0}</p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-700">
              {t('quizRush.personalBest')}{': '}{result?.personal_best ?? 0}
            </span>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-700">
              <span aria-hidden="true">🪙 </span>+{result?.coins_awarded ?? 0}
            </span>
          </div>
          <button
            type="button"
            onClick={() => void start()}
            style={QUIZ_GRADIENT}
            className="mt-1 min-h-[44px] w-full rounded-xl px-4 py-2.5 font-extrabold text-white shadow-sm transition hover:brightness-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500"
          >
            {t('quizRush.playAgain')}
          </button>
          <Link
            to="/arcade"
            className="inline-flex min-h-[44px] items-center text-sm font-semibold text-amber-700 hover:underline focus-visible:outline focus-visible:outline-2"
          >
            {t('quizRush.backToArcade')}
          </Link>
        </div>
      </main>
    );
  }

  // playing phase
  const it = items[idx];
  if (!it) {
    return (
      <main className="p-4 text-center text-sm text-muted-foreground">
        {t('quizRush.noQuestions')}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <div className="flex items-center justify-between" aria-live="polite">
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1.5 text-sm font-bold text-amber-700">
          <span aria-hidden="true">⏱️</span>{t('quizRush.timeLeft')}{': '}{t('quizRush.secondsValue', { count: seconds })}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-3 py-1.5 text-sm font-bold text-brand-700">
          <span aria-hidden="true">🔥</span>{t('quizRush.combo')}{': '}{combo}
        </span>
      </div>
      <h2 className="text-lg font-bold text-ink">{it.question}</h2>
      <ul className="space-y-2.5">
        {it.choices.map((choice, i) => (
          <li key={i}>
            <button
              type="button"
              onClick={() => answer(i)}
              className="block w-full min-h-[44px] rounded-xl border border-line bg-card px-4 py-3 text-left font-semibold text-ink shadow-sm transition active:scale-[0.99] hover:border-brand-300 hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              {choice}
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
