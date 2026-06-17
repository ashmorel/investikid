import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PrivacyNotice } from '@/components/PrivacyNotice';

export default function Privacy() {
  const { t } = useTranslation('parent');
  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="text-2xl font-semibold">{t('privacy.heading')}</h1>
      <PrivacyNotice />
      <p className="mt-8 text-sm text-muted-foreground">
        <Link to="/signup" className="underline">{t('privacy.backToSignUp')}</Link>
        {' · '}
        <Link to="/login" className="underline">{t('privacy.signIn')}</Link>
      </p>
    </main>
  );
}
