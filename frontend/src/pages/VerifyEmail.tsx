import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi, type Me } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { AuthPage } from '@/components/AuthPage';

export default function VerifyEmail() {
  const { t } = useTranslation('auth');
  const [params] = useSearchParams();
  const qc = useQueryClient();
  const token = params.get('token') ?? '';
  const [resendDone, setResendDone] = useState(false);
  const [resendError, setResendError] = useState<string | null>(null);

  const verify = useQuery({
    queryKey: ['verify-email', token],
    queryFn: () => authApi.verifyEmail(token),
    enabled: !!token,
    retry: false,
  });

  useEffect(() => {
    if (verify.isSuccess) {
      const verifiedAt = new Date().toISOString();
      qc.setQueryData<Me | null>(['me'], (current) => (
        current ? { ...current, email_verified_at: current.email_verified_at ?? verifiedAt } : current
      ));
      void qc.invalidateQueries({ queryKey: ['me'] });
    }
  }, [qc, verify.isSuccess]);

  const resend = useMutation({
    mutationFn: () => authApi.resendVerifyEmail(),
    onSuccess: () => setResendDone(true),
    onError: (err) => {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setResendError(t('verifyEmail.error.resendError.needsSignIn'));
      } else {
        setResendError(t('verifyEmail.error.resendError.generic'));
      }
    },
  });

  if (!token) {
    return (
      <AuthPage title={t('verifyEmail.invalidLink.title')} subtitle={t('verifyEmail.invalidLink.subtitle')}>
        <p role="alert" className="text-sm text-destructive">
          {t('verifyEmail.invalidLink.message')}
        </p>
      </AuthPage>
    );
  }

  if (verify.isLoading) {
    return (
      <AuthPage title={t('verifyEmail.loading.title')}>
        <p className="text-sm text-muted-foreground">{t('verifyEmail.loading.message')}</p>
      </AuthPage>
    );
  }

  if (verify.isError) {
    const status = verify.error instanceof ApiError ? verify.error.status : 0;
    const isExpired = status === 410;
    return (
      <AuthPage
        title={isExpired ? t('verifyEmail.error.expiredTitle') : t('verifyEmail.error.genericTitle')}
        subtitle={isExpired ? t('verifyEmail.error.expiredSubtitle') : t('verifyEmail.error.genericSubtitle')}
      >
        <p className="text-sm text-muted-foreground">
          {isExpired
            ? t('verifyEmail.error.expiredMessage')
            : t('verifyEmail.error.genericMessage')}
        </p>
        {!isExpired && (
          <p className="mt-4 text-sm text-muted-foreground">
            <Link to="/login" className="underline">{t('verifyEmail.error.backToSignIn')}</Link>
          </p>
        )}
        {isExpired && (
          <div className="mt-4">
            {resendDone ? (
              <p className="text-sm text-muted-foreground">
                {t('verifyEmail.error.resendDone')}
              </p>
            ) : (
              <>
                <Button
                  onClick={() => { setResendError(null); resend.mutate(); }}
                  disabled={resend.isPending}
                  variant="outline"
                >
                  {resend.isPending ? t('verifyEmail.error.sending') : t('verifyEmail.error.resendButton')}
                </Button>
                {resendError && (
                  <p role="alert" className="mt-2 text-sm text-destructive">{resendError}</p>
                )}
              </>
            )}
          </div>
        )}
      </AuthPage>
    );
  }

  return (
    <AuthPage title={t('verifyEmail.success.title')}>
      <p className="text-sm text-muted-foreground">
        {t('verifyEmail.success.message')}
      </p>
      <p className="mt-4 text-sm text-muted-foreground">
        <Link to="/home" className="underline">{t('verifyEmail.success.goHome')}</Link>
        {' · '}
        <Link to="/login" className="underline">{t('verifyEmail.success.signIn')}</Link>
      </p>
    </AuthPage>
  );
}
