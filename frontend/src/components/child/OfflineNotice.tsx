import { useTranslation } from 'react-i18next';

type Props = { className?: string };

/** Friendly inline notice for live-price surfaces when the device is offline. */
export function OfflineNotice({ className }: Props) {
  const { t } = useTranslation('child');
  return (
    <p
      role="status"
      className={`rounded-xl border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm font-medium text-brand-700 ${className ?? ''}`}
    >
      {t('offline.notice')}
    </p>
  );
}
