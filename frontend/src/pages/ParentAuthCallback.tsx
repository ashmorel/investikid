import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { parentApi } from '@/api/parent';
import { ApiError } from '@/api/client';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Button } from '@/components/ui/button';

type State = 'pending' | 'gone' | 'error';

export default function ParentAuthCallback() {
  const { t } = useTranslation('parent');
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const navigate = useNavigate();
  const [state, setState] = useState<State>('pending');

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- setting 'gone' synchronously when token is missing avoids an unnecessary async round-trip
    if (!token) { setState('gone'); return; }
    parentApi.magicCallback(token)
      .then(() => navigate('/parent', { replace: true }))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 410) setState('gone');
        else setState('error');
      });
  }, [token, navigate]);

  if (state === 'pending') {
    return <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6"><p>{t('authCallback.signingIn')}</p></main>;
  }

  return (
    <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
      <ErrorBanner
        title={t(state === 'gone' ? 'authCallback.linkExpiredTitle' : 'authCallback.errorTitle')}
        message={t(state === 'gone' ? 'authCallback.linkExpiredMessage' : 'authCallback.errorMessage')}
        action={
          <Button asChild variant="outline">
            <Link to="/parent/login">{t('authCallback.requestNewLink')}</Link>
          </Button>
        }
      />
    </main>
  );
}
