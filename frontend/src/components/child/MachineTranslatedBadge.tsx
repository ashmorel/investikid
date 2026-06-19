import { useTranslation } from 'react-i18next';

/** Small muted sky-blue chip shown on content that was machine-translated
 *  (auto-translated, not human-curated). Decorative-but-informative label. */
export function MachineTranslatedBadge() {
  const { t } = useTranslation('common');
  return (
    <span className="inline-flex items-center rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-600">
      {t('machineTranslated')}
    </span>
  );
}
