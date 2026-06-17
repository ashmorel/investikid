import { useTranslation } from 'react-i18next';

/** Small pill marking the investor (14–18) experience. Rendered only when tierConfig.showTierChip. */
export function TierChip() {
  const { t } = useTranslation('child');
  return (
    <span
      aria-label={t('tierChip.label')}
      className="inline-flex items-center rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700"
    >
      {t('tierChip.text')}
    </span>
  );
}
