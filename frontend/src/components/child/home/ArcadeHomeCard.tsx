import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function ArcadeHomeCard() {
  const { t } = useTranslation('arcade');
  return (
    <Link
      to="/arcade"
      className="block rounded-xl border border-line bg-card p-4 min-h-[44px] focus-visible:outline focus-visible:outline-2"
    >
      <div className="text-base font-extrabold text-ink">🎮 {t('home.cardTitle')}</div>
      <div className="text-sm text-muted-foreground">{t('home.cardCta')}</div>
    </Link>
  );
}
