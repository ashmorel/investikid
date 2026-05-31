import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, type Me } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';

interface Props {
  profile: Me;
}

export function VerifyEmailBanner({ profile }: Props) {
  const qc = useQueryClient();
  const [dismissed, setDismissed] = useState(false);
  const [resendDone, setResendDone] = useState(false);
  const [resendError, setResendError] = useState<string | null>(null);

  const resend = useMutation({
    mutationFn: () => authApi.resendVerifyEmail(),
    onSuccess: async () => {
      setResendDone(true);
      setResendError(null);
      await qc.invalidateQueries({ queryKey: ['me'] });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 429) {
        setResendError('Please wait before requesting another email.');
      } else {
        setResendError('Could not send right now. Try again.');
      }
    },
  });

  // Only show when user has an email and it is not yet verified
  if (!profile.email || profile.email_verified_at !== null || dismissed) {
    return null;
  }

  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-4 border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900"
    >
      <span>
        Please confirm your email address.{' '}
        {resendDone ? (
          <span className="font-medium">Verification email sent — check your inbox.</span>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="h-auto p-0 text-amber-900 underline hover:bg-transparent"
            onClick={() => { setResendError(null); resend.mutate(); }}
            disabled={resend.isPending}
          >
            {resend.isPending ? 'Sending…' : 'Resend'}
          </Button>
        )}
        {resendError && <span className="ml-2 font-medium">{resendError}</span>}
      </span>
      <button
        type="button"
        aria-label="Dismiss"
        className="text-amber-700 hover:text-amber-900"
        onClick={() => setDismissed(true)}
      >
        ✕
      </button>
    </div>
  );
}
