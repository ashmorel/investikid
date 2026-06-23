import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getQuizRushSession, submitQuizRushScore, type QuizItem, type QuizScoreResult } from '@/api/arcade';

const ROUND_SECONDS = 60;
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
      <main className="mx-auto max-w-md space-y-4 p-4 text-center">
        <h1 className="text-xl font-extrabold text-ink">&#9889; {t('quizRush.name')}</h1>
        <p className="text-sm text-muted-foreground">{t('quizRush.tagline')}</p>
        <button
          type="button"
          onClick={() => void start()}
          className="min-h-[44px] rounded-md bg-brand-600 px-6 py-2 font-semibold text-white focus-visible:outline focus-visible:outline-2"
        >
          {t('quizRush.start')}
        </button>
      </main>
    );
  }

  if (phase === 'done') {
    return (
      <main className="mx-auto max-w-md space-y-3 p-4 text-center">
        <h2 className="text-lg font-extrabold text-ink">{t('quizRush.results')}</h2>
        <p className="text-3xl font-extrabold text-ink">{result?.points ?? 0}</p>
        <p className="text-sm text-muted-foreground">
          {t('quizRush.personalBest')}{': '}{result?.personal_best ?? 0}
        </p>
        <p className="text-sm text-muted-foreground">
          {t('quizRush.coinsEarned')}{': '}{result?.coins_awarded ?? 0}
        </p>
        <div className="flex justify-center gap-2">
          <button
            type="button"
            onClick={() => void start()}
            className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 font-semibold text-white focus-visible:outline focus-visible:outline-2"
          >
            {t('quizRush.playAgain')}
          </button>
          <Link
            to="/arcade"
            className="inline-flex min-h-[44px] items-center rounded-md border border-line px-4 py-2 font-semibold text-ink focus-visible:outline focus-visible:outline-2"
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
      <div className="flex justify-between text-sm font-semibold text-ink" aria-live="polite">
        <span>{t('quizRush.timeLeft')}{': '}{t('quizRush.secondsValue', { count: seconds })}</span>
        <span>{t('quizRush.combo')}{': '}{combo}</span>
      </div>
      <h2 className="text-lg font-bold text-ink">{it.question}</h2>
      <ul className="space-y-2">
        {it.choices.map((choice, i) => (
          <li key={i}>
            <button
              type="button"
              onClick={() => answer(i)}
              className="block w-full min-h-[44px] rounded-md border border-line bg-card px-4 py-2 text-left text-ink focus-visible:outline focus-visible:outline-2"
            >
              {choice}
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
