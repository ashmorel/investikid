import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CoachChat } from '@/components/child/CoachChat';

export default function Coach() {
  const { t } = useTranslation('child');
  return (
    <div className="mx-auto flex h-[calc(100svh-8rem)] max-w-2xl flex-col px-4 py-4">
      <Link
        to="/home"
        aria-label={t('coach.backAriaLabel')}
        className="mb-3 inline-flex w-fit items-center text-sm font-medium text-brand-700 hover:text-brand-900"
      >
        {t('coach.back')}
      </Link>
      <CoachChat />
    </div>
  );
}
