import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getMoneyWordToday, submitMoneyWordGuess, type MoneyWordState } from '@/api/moneyword';

type LoadState = 'loading' | 'error' | 'ready';

const FEEDBACK_EMOJI: Record<string, string> = {
  correct: '🟩',
  present: '🟨',
  absent: '⬛',
};

const FEEDBACK_SYMBOL: Record<string, string> = {
  correct: '✓',
  present: '◐',
  absent: '✕',
};

const KEYBOARD_ROWS = [
  ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
  ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
  ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
];

export default function MoneyWord() {
  const { t } = useTranslation('arcade');
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [gameState, setGameState] = useState<MoneyWordState | null>(null);
  const [current, setCurrent] = useState('');
  const [announcement, setAnnouncement] = useState('');
  const [shareMsg, setShareMsg] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    void (async () => {
      const state = await getMoneyWordToday();
      if (!isMounted.current) return;
      if (state === null) {
        setLoadState('error');
      } else {
        setGameState(state);
        setLoadState('ready');
      }
    })();
    return () => {
      isMounted.current = false;
    };
  }, []);

  const pressLetter = useCallback(
    (letter: string) => {
      if (!gameState || gameState.completed) return;
      setCurrent((c) => (c.length < gameState.length ? c + letter : c));
    },
    [gameState],
  );

  const pressBackspace = useCallback(() => {
    setCurrent((c) => c.slice(0, -1));
  }, []);

  const pressEnter = useCallback(async () => {
    if (!gameState || submitting || gameState.completed) return;
    if (current.length !== gameState.length) return;
    setSubmitting(true);
    const result = await submitMoneyWordGuess(current);
    if (!isMounted.current) return;
    setSubmitting(false);
    if (result === null) {
      setAnnouncement(t('moneyword.guessError'));
      return;
    }
    setCurrent('');
    setGameState(result);
    const remaining = result.max_guesses - result.guesses.length;
    if (result.completed) {
      setAnnouncement(result.solved ? t('moneyword.solved') : t('moneyword.failed'));
    } else {
      setAnnouncement(t('moneyword.guessesLeft', { count: remaining }));
    }
  }, [gameState, submitting, current, t]);

  const shareResult = useCallback(async () => {
    if (!gameState) return;
    const header = t('moneyword.shareHeader');
    const grid = gameState.guesses
      .map((g) => g.feedback.map((f) => FEEDBACK_EMOJI[f] ?? '⬛').join(''))
      .join('\n');
    const text = `${header}\n${grid}`;
    // Prefer the native share sheet (mobile / iOS Safari); fall back to the
    // clipboard. Either way, give visible + announced confirmation — the old
    // version copied silently, so it looked like nothing happened.
    if (typeof navigator.share === 'function') {
      try {
        await navigator.share({ text });
        return;
      } catch (err) {
        // User dismissed the share sheet — leave quietly, no error message.
        if (err instanceof DOMException && err.name === 'AbortError') return;
        // Any other failure: fall through to the clipboard path below.
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      setShareMsg(t('moneyword.shareCopied'));
      setAnnouncement(t('moneyword.shareCopied'));
    } catch {
      setShareMsg(t('moneyword.shareFailed'));
      setAnnouncement(t('moneyword.shareFailed'));
    }
  }, [gameState, t]);

  if (loadState === 'loading') {
    return (
      <main className="p-4 text-center text-sm text-muted-foreground" aria-live="polite">
        {t('moneyword.loading')}
      </main>
    );
  }

  if (loadState === 'error' || !gameState) {
    return (
      <main className="p-4 text-center text-sm text-muted-foreground">
        <p>{t('moneyword.loadError')}</p>
        <Link
          to="/arcade"
          className="mt-2 inline-flex min-h-[44px] items-center rounded-md border border-line px-4 py-2 font-semibold text-ink focus-visible:outline focus-visible:outline-2"
        >
          {t('moneyword.backToArcade')}
        </Link>
      </main>
    );
  }

  const { length, max_guesses, guesses, completed, solved, definition } = gameState;
  const isComplete = completed || gameState.already_played;

  // Build grid rows
  const rows: { letters: string[]; feedback: string[] | null }[] = [];
  for (let r = 0; r < max_guesses; r++) {
    if (r < guesses.length) {
      rows.push({ letters: guesses[r].word.split(''), feedback: guesses[r].feedback });
    } else if (!isComplete && r === guesses.length) {
      // Current input row
      const letters = current.split('');
      while (letters.length < length) letters.push('');
      rows.push({ letters, feedback: null });
    } else {
      rows.push({ letters: Array(length).fill('') as string[], feedback: null });
    }
  }

  return (
    <main className="mx-auto max-w-md space-y-4 p-4 text-center">
      <h1 className="text-xl font-extrabold text-ink">{t('moneyword.name')}</h1>

      {/* How to play */}
      <details
        open={guesses.length === 0 && !isComplete}
        className="rounded-xl border border-line bg-card p-3 text-left text-sm"
      >
        <summary className="min-h-[44px] cursor-pointer list-none font-semibold text-ink">
          ❓ {t('moneyword.howToPlay.title')}
        </summary>
        <div className="mt-2 space-y-2 text-muted-foreground">
          <p>{t('moneyword.howToPlay.intro', { count: max_guesses })}</p>
          <p>{t('moneyword.howToPlay.step1')}</p>
          <p>{t('moneyword.howToPlay.step2')}</p>
          <ul className="space-y-1">
            {(
              [
                ['correct', 'bg-green-500 border-green-600', 'legendCorrect'],
                ['present', 'bg-yellow-400 border-yellow-500', 'legendPresent'],
                ['absent', 'bg-gray-400 border-gray-500', 'legendAbsent'],
              ] as const
            ).map(([state, color, labelKey]) => (
              <li key={state} className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className={`flex h-7 w-7 shrink-0 flex-col items-center justify-center rounded border-2 text-xs font-bold text-white ${color}`}
                >
                  <span>{t('moneyword.howToPlay.exampleLetter')}</span>
                  <span className="text-[8px] leading-none">{FEEDBACK_SYMBOL[state]}</span>
                </span>
                <span>{t(`moneyword.howToPlay.${labelKey}`)}</span>
              </li>
            ))}
          </ul>
          <p>{t('moneyword.howToPlay.step3')}</p>
        </div>
      </details>

      {/* aria-live region for announcements */}
      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      {/* Grid */}
      <div
        role="grid"
        aria-label={t('moneyword.gridLabel')}
        className="inline-flex flex-col gap-1"
      >
        {rows.map((row, ri) => (
          <div key={ri} role="row" className="flex gap-1">
            {row.letters.map((letter, ci) => {
              const fb = row.feedback?.[ci] ?? null;
              const symbol = fb ? (FEEDBACK_SYMBOL[fb] ?? '') : '';
              const ariaLabel = fb
                ? t(`moneyword.tileLabel.${fb}`, { letter: letter || ' ' })
                : letter || '';
              const bgClass =
                fb === 'correct'
                  ? 'bg-green-500 text-white border-green-600'
                  : fb === 'present'
                    ? 'bg-yellow-400 text-white border-yellow-500'
                    : fb === 'absent'
                      ? 'bg-gray-400 text-white border-gray-500'
                      : 'bg-card border-line';
              return (
                <div
                  key={`${ri}-${ci}`}
                  role="gridcell"
                  aria-label={ariaLabel}
                  className={`flex h-12 w-12 flex-col items-center justify-center rounded border-2 text-sm font-bold text-ink ${bgClass}`}
                >
                  <span aria-hidden="true">{letter.toUpperCase()}</span>
                  {symbol && (
                    <span className="text-[10px] leading-none" aria-hidden="true">
                      {symbol}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Completed state */}
      {isComplete && (
        <div className="space-y-3">
          {solved ? (
            <p className="font-extrabold text-green-600">
              {t('moneyword.solvedMessage', { count: guesses.length })}
            </p>
          ) : (
            <p className="font-extrabold text-red-600">{t('moneyword.failedMessage')}</p>
          )}
          {definition && (
            <div className="rounded-lg border border-line bg-card p-3 text-left text-sm text-ink">
              <p className="font-semibold text-muted-foreground">{t('moneyword.definitionLabel')}</p>
              <p>{definition}</p>
            </div>
          )}
          <div className="flex justify-center gap-2">
            <button
              type="button"
              onClick={shareResult}
              className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 font-semibold text-white focus-visible:outline focus-visible:outline-2"
            >
              {t('moneyword.share')}
            </button>
            <Link
              to="/arcade"
              className="inline-flex min-h-[44px] items-center rounded-md border border-line px-4 py-2 font-semibold text-ink focus-visible:outline focus-visible:outline-2"
            >
              {t('moneyword.backToArcade')}
            </Link>
          </div>
          {shareMsg && (
            <p role="status" className="text-sm font-semibold text-brand-700">
              {shareMsg}
            </p>
          )}
        </div>
      )}

      {/* On-screen keyboard */}
      {!isComplete && (
        <div className="space-y-1" role="group" aria-label={t('moneyword.keyboardLabel')}>
          {KEYBOARD_ROWS.map((row, ri) => (
            <div key={ri} className="flex justify-center gap-1">
              {row.map((letter) => (
                <button
                  key={letter}
                  type="button"
                  aria-label={letter}
                  onClick={() => pressLetter(letter)}
                  disabled={submitting}
                  className="min-h-[44px] min-w-[44px] rounded border border-line bg-card text-sm font-bold text-ink focus-visible:outline focus-visible:outline-2 disabled:opacity-50"
                >
                  {letter}
                </button>
              ))}
            </div>
          ))}
          <div className="flex justify-center gap-1">
            <button
              type="button"
              onClick={() => void pressEnter()}
              disabled={submitting || current.length !== (gameState?.length ?? 0)}
              className="min-h-[44px] rounded bg-brand-600 px-3 text-sm font-semibold text-white focus-visible:outline focus-visible:outline-2 disabled:opacity-50"
            >
              {t('moneyword.enter')}
            </button>
            <button
              type="button"
              aria-label={t('moneyword.backspace')}
              onClick={pressBackspace}
              disabled={submitting}
              className="min-h-[44px] min-w-[2.25rem] rounded border border-line bg-card text-sm font-bold text-ink focus-visible:outline focus-visible:outline-2 disabled:opacity-50"
            >
              {'⌫'}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
