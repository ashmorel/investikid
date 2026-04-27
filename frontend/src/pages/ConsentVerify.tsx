import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { consentApi, type Decision } from '@/api/consent';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/ErrorBanner';

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
      <Page>
        <ErrorBanner title="Invalid link" message="This link is missing its token." />
      </Page>
    );
  }

  if (peek.isLoading) return <Page><p>Loading…</p></Page>;

  if (peek.isError) {
    const status = peek.error instanceof ApiError ? peek.error.status : 0;
    const message = status === 410
      ? 'This link is invalid, expired, or already used.'
      : 'Something went wrong. Please try again.';
    return <Page><ErrorBanner title="Link unavailable" message={message} /></Page>;
  }

  if (done === 'approve') {
    return <Page><Success title="Account approved" message="Your child can now sign in to Invest-Ed." /></Page>;
  }
  if (done === 'decline') {
    return <Page><Success title="Decision recorded" message="The account will remain inactive." /></Page>;
  }

  const child = peek.data!;
  const decideError = decide.error instanceof ApiError ? decide.error : null;

  return (
    <Page>
      <h1 className="text-2xl font-semibold">Approve your child's account?</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{child.username}</span> ({child.age}, {child.country_code})
        signed up for Invest-Ed and listed you as their parent.
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
    </Page>
  );
}

function Page({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-lg p-6">{children}</main>;
}

function Success({ title, message }: { title: string; message: string }) {
  return (
    <div role="status" className="rounded-md border bg-muted/30 p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
