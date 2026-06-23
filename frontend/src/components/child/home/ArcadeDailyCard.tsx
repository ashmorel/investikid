import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMoneyWordToday } from '@/api/moneyword';

export default function ArcadeDailyCard() {
  const { t } = useTranslation('arcade');
  const { data } = useMoneyWordToday();

  let label: string;
  let sub: string | null = null;

  if (!data || (!data.completed && data.guesses.length === 0)) {
    // Not started (or null/failed — degrade to Play)
    label = t('dailyCard.play');
  } else if (!data.completed) {
    // In progress
    label = t('dailyCard.continue');
    sub = t('dailyCard.guessesUsed', { count: data.guesses.length, max: data.max_guesses });
  } else {
    // Completed
    label = t('dailyCard.done');
  }

  return (
    <Link
      to="/arcade/moneyword"
      aria-label={t('dailyCard.ariaLabel', { state: label })}
      className="block rounded-xl border border-line bg-card p-4 min-h-[44px] focus-visible:outline focus-visible:outline-2"
    >
      <div className="text-base font-extrabold text-ink">
        🟩 {t('dailyCard.title')} — {label}
      </div>
      {sub && <div className="text-sm text-muted-foreground">{sub}</div>}
    </Link>
  );
}
