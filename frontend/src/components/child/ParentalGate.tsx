import { useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { checkAnswer, makeChallenge } from '@/lib/parentalGate';

/** A lightweight "ask a grown-up" gate shown before the native purchase sheet.
 *  This is FRICTION, not authentication — the real spend authorization is the OS
 *  purchase sheet + Ask-to-Buy. Reusable; not wired into the paywall yet. */
export function ParentalGate({
  onPass,
  onCancel,
  rng,
}: {
  onPass: () => void;
  onCancel: () => void;
  rng?: () => number;
}) {
  const { t } = useTranslation('child');
  const [challenge] = useState(() => makeChallenge(rng));
  const [input, setInput] = useState('');
  const [error, setError] = useState(false);
  const inputId = useId();

  function submit() {
    if (checkAnswer(challenge, input)) {
      onPass();
    } else {
      setError(true);
    }
  }

  return (
    <section
      role="group"
      aria-label={t('parentalGate.title')}
      className="rounded-2xl border border-brand-100 bg-white p-4 text-ink"
    >
      <h2 className="text-base font-bold text-ink">{t('parentalGate.title')}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{t('parentalGate.subtitle')}</p>

      <label htmlFor={inputId} className="mt-4 block text-sm font-semibold text-ink">
        {t('parentalGate.questionLabel', { prompt: challenge.prompt })}
      </label>
      <input
        id={inputId}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        aria-label={t('parentalGate.answerLabel')}
        aria-invalid={error || undefined}
        value={input}
        onChange={(e) => { setInput(e.target.value); setError(false); }}
        className="mt-2 w-full rounded-xl border border-brand-100 px-4 py-3 text-base text-ink focus:outline-none focus:ring-2 focus:ring-brand-400"
      />

      {error && (
        <p role="alert" className="mt-2 text-sm font-semibold text-red-600">
          {t('parentalGate.tryAgain')}
        </p>
      )}

      <div className="mt-4 flex flex-col gap-2">
        <button
          type="button"
          onClick={submit}
          className="min-h-11 w-full rounded-full bg-brand-gradient px-5 py-3 text-sm font-bold text-white shadow focus:outline-none focus:ring-2 focus:ring-brand-400"
        >
          {t('parentalGate.continue')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 w-full rounded-full px-5 py-2 text-sm font-semibold text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand-400"
        >
          {t('parentalGate.cancel')}
        </button>
      </div>
    </section>
  );
}
