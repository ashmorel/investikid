import { useSearchParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { consentApi, type Decision } from '@/api/consent';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/ErrorBanner';
import { AuthPage } from '@/components/AuthPage';

export default function ConsentVerify() {
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const [done, setDone] = useState<Decision | null>(null);
  const [attested, setAttested] = useState(false);

  const peek = useQuery({
    queryKey: ['consent.verify', token],
    queryFn: () => consentApi.verify(token),
    enabled: !!token,
    retry: false,
  });

  const decide = useMutation({
    mutationFn: (d: Decision) => consentApi.decide(token, d, d === 'approve' ? attested : false),
    onSuccess: (_res, d) => {
      if (d === 'approve') { navigate('/parent'); } else { setDone(d); }
    },
  });

  if (!token) {
    return (
      <AuthPage title={t('consentVerify.invalidLink.title')} subtitle={t('consentVerify.invalidLink.subtitle')}>
        <ErrorBanner title={t('consentVerify.invalidLink.errorTitle')} message={t('consentVerify.invalidLink.errorMessage')} />
      </AuthPage>
    );
  }

  if (peek.isLoading) {
    return (
      <AuthPage title={t('consentVerify.loading.title')}>
        <p className="text-sm text-muted-foreground">{t('consentVerify.loading.message')}</p>
      </AuthPage>
    );
  }

  if (peek.isError) {
    const status = peek.error instanceof ApiError ? peek.error.status : 0;
    const message = status === 410
      ? t('consentVerify.linkUnavailable.errorExpired')
      : t('consentVerify.linkUnavailable.errorGeneric');
    return (
      <AuthPage title={t('consentVerify.linkUnavailable.title')} subtitle={t('consentVerify.linkUnavailable.subtitle')}>
        <ErrorBanner title={t('consentVerify.linkUnavailable.errorTitle')} message={message} />
      </AuthPage>
    );
  }

  if (done === 'approve') {
    return (
      <AuthPage title={t('consentVerify.approved.title')}>
        <Success message={t('consentVerify.approved.message')} />
      </AuthPage>
    );
  }
  if (done === 'decline') {
    return (
      <AuthPage title={t('consentVerify.declined.title')}>
        <Success message={t('consentVerify.declined.message')} />
      </AuthPage>
    );
  }

  const child = peek.data!;
  const decideError = decide.error instanceof ApiError ? decide.error : null;

  return (
    <AuthPage title={t('consentVerify.review.title')} subtitle={t('consentVerify.review.subtitle')}>
      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{child.username}</span>{' '}
        ({child.age}, {child.country_code}){' '}
        {t('consentVerify.review.childSuffix')}
      </p>
      {decideError && (
        <ErrorBanner
          className="mt-4"
          title={decideError.status === 410 ? t('consentVerify.review.errorLinkExpired') : t('consentVerify.review.errorGeneric')}
          message={decideError.detail}
        />
      )}
      <div className="mt-6 flex items-start gap-3">
        <input
          id="guardian-attest"
          type="checkbox"
          checked={attested}
          onChange={(e) => setAttested(e.target.checked)}
          className="mt-1 h-4 w-4"
        />
        <label htmlFor="guardian-attest" className="text-sm text-foreground">
          {t('consentVerify.review.attestLabel', { username: child.username })}
        </label>
      </div>
      <div className="mt-6 flex gap-3">
        <Button onClick={() => decide.mutate('approve')} disabled={!attested || decide.isPending}>
          {t('consentVerify.review.approve')}
        </Button>
        <Button variant="outline" onClick={() => decide.mutate('decline')} disabled={decide.isPending}>
          {t('consentVerify.review.decline')}
        </Button>
      </div>
    </AuthPage>
  );
}

function Success({ message }: { message: string }) {
  return (
    <div role="status" className="rounded-md border bg-muted/30 p-6">
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
