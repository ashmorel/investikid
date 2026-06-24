import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useProgress } from '@/hooks/useProgress';

const QUIZ_GRADIENT = { background: 'linear-gradient(135deg, #ea580c, #dc2626)' };
const WORD_GRADIENT = { background: 'linear-gradient(135deg, #16a34a, #15803d)' };

export default function Arcade() {
  const { t } = useTranslation('arcade');
  const { data: progress } = useProgress();
  const coins = progress?.virtual_coins ?? 0;

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-xl font-extrabold text-ink">
          <span aria-hidden="true">🎮 </span>{t('hub.title')}
        </h1>
        <span
          className="inline-flex items-center gap-1 rounded-xl bg-amber-100 px-2.5 py-1.5 text-sm font-bold text-amber-700"
          aria-label={t('hub.coinsAria', { count: coins })}
        >
          <span aria-hidden="true">🪙</span>
          {coins}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{t('hub.subtitle')}</p>

      <ul className="space-y-3">
        <li>
          <Link
            to="/arcade/quiz-rush"
            style={QUIZ_GRADIENT}
            className="block min-h-[44px] rounded-2xl p-5 text-white shadow-md transition hover:brightness-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-3xl" aria-hidden="true">⚡</span>
              <span className="rounded-full bg-white/90 px-2.5 py-1 text-xs font-bold text-amber-700">
                {t('hub.playChip')}
              </span>
            </div>
            <div className="mt-2 text-lg font-extrabold">{t('quizRush.name')}</div>
            <div className="text-sm text-white/85">{t('quizRush.tagline')}</div>
          </Link>
        </li>
        <li>
          <Link
            to="/arcade/moneyword"
            style={WORD_GRADIENT}
            className="block min-h-[44px] rounded-2xl p-5 text-white shadow-md transition hover:brightness-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green-600"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-3xl" aria-hidden="true">🟩</span>
              <span className="rounded-full bg-white/90 px-2.5 py-1 text-xs font-bold text-green-700">
                {t('hub.playChip')}
              </span>
            </div>
            <div className="mt-2 text-lg font-extrabold">{t('moneyword.name')}</div>
            <div className="text-sm text-white/85">{t('moneyword.tagline')}</div>
          </Link>
        </li>
      </ul>
      <p className="text-center text-xs text-muted-foreground">{t('hub.moreSoon')}</p>
    </main>
  );
}
