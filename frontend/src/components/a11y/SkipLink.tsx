import { useTranslation } from 'react-i18next';

export function SkipLink() {
  const { t } = useTranslation('common');
  return (
    <a
      href="#main"
      className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-brand-900 focus:shadow focus:outline focus:outline-2 focus:outline-brand-600"
    >
      {t('skipToMain')}
    </a>
  );
}
