import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { authApi, type Me } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { AuthPage } from '@/components/AuthPage';

export default function VerifyEmail() {
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
        setResendError('Please sign in and try again from the banner.');
      } else {
        setResendError('Something went wrong. Please try again.');
      }
    },
  });

  if (!token) {
    return (
      <AuthPage title="That link didn't work" subtitle="Please use the verification link from your email.">
        <p role="alert" className="text-sm text-destructive">
          Invalid link. Please use the verification link from your email.
        </p>
      </AuthPage>
    );
  }

  if (verify.isLoading) {
    return (
      <AuthPage title="Verifying your email...">
        <p className="text-sm text-muted-foreground">This should only take a moment.</p>
      </AuthPage>
    );
  }

  if (verify.isError) {
    const status = verify.error instanceof ApiError ? verify.error.status : 0;
    const isExpired = status === 410;
    return (
      <AuthPage
        title={isExpired ? 'That link expired' : 'That link didn’t work'}
        subtitle={isExpired ? 'Request a fresh verification email.' : 'Try again or head back to sign in.'}
      >
        <p className="text-sm text-muted-foreground">
          {isExpired
            ? 'This link is invalid or expired.'
            : 'Something went wrong. Please try again.'}
        </p>
        {!isExpired && (
          <p className="mt-4 text-sm text-muted-foreground">
            <Link to="/login" className="underline">Back to sign in</Link>
          </p>
        )}
        {isExpired && (
          <div className="mt-4">
            {resendDone ? (
              <p className="text-sm text-muted-foreground">
                Verification email sent. Check your inbox.
              </p>
            ) : (
              <>
                <Button
                  onClick={() => { setResendError(null); resend.mutate(); }}
                  disabled={resend.isPending}
                  variant="outline"
                >
                  {resend.isPending ? 'Sending…' : 'Resend verification email'}
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
    <AuthPage title="Email verified!">
      <p className="text-sm text-muted-foreground">
        Your email is confirmed. You're all set.
      </p>
      <p className="mt-4 text-sm text-muted-foreground">
        <Link to="/home" className="underline">Go to your home page</Link>
        {' · '}
        <Link to="/login" className="underline">Sign in</Link>
      </p>
    </AuthPage>
  );
}
