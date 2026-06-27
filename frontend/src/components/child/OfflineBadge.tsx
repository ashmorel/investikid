// frontend/src/components/child/OfflineBadge.tsx
import { CheckCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/** Pill shown on a level card when that level's lessons are fully cached and available offline. */
export function OfflineBadge() {
  const { t } = useTranslation('child');
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border border-brand-200 bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
    >
      <CheckCircle2 className="h-3 w-3 shrink-0" aria-hidden="true" />
      {t('offline.available')}
    </span>
  );
}
