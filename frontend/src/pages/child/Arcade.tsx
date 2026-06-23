import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function Arcade() {
  const { t } = useTranslation('arcade');
  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <h1 className="text-xl font-extrabold text-ink">{t('hub.title')}</h1>
      <p className="text-sm text-muted-foreground">{t('hub.subtitle')}</p>
      <ul className="space-y-3">
        <li>
          <Link
            to="/arcade/quiz-rush"
            className="block rounded-xl border border-line bg-card p-4 min-h-[44px]"
          >
            <div className="text-base font-extrabold text-ink">⚡ {t('quizRush.name')}</div>
            <div className="text-sm text-muted-foreground">{t('quizRush.tagline')}</div>
          </Link>
        </li>
      </ul>
    </main>
  );
}
