import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { consentApi, type Decision } from '@/api/consent';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/ErrorBanner';
import { AuthPage } from '@/components/AuthPage';

export default function ConsentVerify() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const [done, setDone] = useState<Decision | null>(null);

  const peek = useQuery({
    queryKey: ['consent.verify', token],
    queryFn: () => consentApi.verify(token),
    enabled: !!token,
    retry: false,
  });

  const decide = useMutation({
    mutationFn: (d: Decision) => consentApi.decide(token, d),
    onSuccess: (_data, d) => setDone(d),
  });

  if (!token) {
    return (
      <AuthPage title="That link didn't work" subtitle="Please use the approval link from your email.">
        <ErrorBanner title="Invalid link" message="This link is missing its token." />
      </AuthPage>
    );
  }

  if (peek.isLoading) {
    return (
      <AuthPage title="Checking the approval link...">
        <p className="text-sm text-muted-foreground">This should only take a moment.</p>
      </AuthPage>
    );
  }

  if (peek.isError) {
    const status = peek.error instanceof ApiError ? peek.error.status : 0;
    const message = status === 410
      ? 'This link is invalid, expired, or already used.'
      : 'Something went wrong. Please try again.';
    return (
      <AuthPage title="Link unavailable" subtitle="This approval link may have already been used.">
        <ErrorBanner title="Link unavailable" message={message} />
      </AuthPage>
    );
  }

  if (done === 'approve') {
    return (
      <AuthPage title="All set — thank you!">
        <Success message="Your child can now sign in to InvestiKid." />
      </AuthPage>
    );
  }
  if (done === 'decline') {
    return (
      <AuthPage title="Decision recorded">
        <Success message="The account will remain inactive." />
      </AuthPage>
    );
  }

  const child = peek.data!;
  const decideError = decide.error instanceof ApiError ? decide.error : null;

  return (
    <AuthPage title="Approve your child's account" subtitle="Review the request before your child signs in.">
      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{child.username}</span> ({child.age}, {child.country_code})
        signed up for InvestiKid and listed you as their parent.
      </p>
      {decideError && (
        <ErrorBanner
          className="mt-4"
          title={decideError.status === 410 ? 'Link no longer valid' : 'Something went wrong'}
          message={decideError.detail}
        />
      )}
      <div className="mt-6 flex gap-3">
        <Button onClick={() => decide.mutate('approve')} disabled={decide.isPending}>
          Approve
        </Button>
        <Button variant="outline" onClick={() => decide.mutate('decline')} disabled={decide.isPending}>
          Decline
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
