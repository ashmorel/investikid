import { useTranslation } from 'react-i18next';

export function PremiumBadge({ className }: { className?: string }) {
  const { t } = useTranslation('child');
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-accent-100 px-2 py-0.5 text-xs font-semibold text-accent-700 ${className ?? ''}`}
    >
      <span aria-hidden="true">✨</span> {t('premiumBadge.text')}
    </span>
  );
}
