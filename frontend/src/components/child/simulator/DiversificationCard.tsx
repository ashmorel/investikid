import { useTranslation } from 'react-i18next';

const BAND_KEYS: { max: number; key: string }[] = [
  { max: 0, key: 'none' },
  { max: 1, key: 'oneBasket' },
  { max: 3, key: 'spread' },
  { max: 5, key: 'nice' },
  { max: Infinity, key: 'well' },
];

export function DiversificationCard({ holdingsCount }: { holdingsCount: number }) {
  const { t } = useTranslation('simulator');
  const labelKey = BAND_KEYS.find((b) => holdingsCount <= b.max)!.key;
  const filled = Math.min(holdingsCount, 5);

  return (
    <div className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold text-muted-foreground">{t('diversification.label')}</p>
        <span className="text-xl" aria-hidden="true">🧺</span>
      </div>
      <p className="mt-0.5 text-lg font-extrabold text-ink">{t(`diversification.bands.${labelKey}`)}</p>
      <div
        role="progressbar"
        aria-label={t('diversification.ariaLabel')}
        aria-valuemin={0}
        aria-valuemax={5}
        aria-valuenow={filled}
        aria-valuetext={t('diversification.ariaValueText', { filled })}
        className="mt-2 flex gap-1"
      >
        {Array.from({ length: 5 }, (_, i) => (
          <div
            key={i}
            className={`h-2 flex-1 rounded-full ${i < filled ? 'bg-brand-500' : 'bg-brand-100'}`}
          />
        ))}
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {t('diversification.body')}
      </p>
    </div>
  );
}
