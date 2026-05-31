import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

type State =
  | { kind: 'idle' }
  | { kind: 'recheck' }
  | { kind: 'still-pending' }
  | { kind: 'declined' }
  | { kind: 'invalid' };

export default function PendingConsent() {
  const email = sessionStorage.getItem('pendingConsentEmail') ?? '';
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [state, setState] = useState<State>({ kind: 'idle' });
  const [password, setPassword] = useState('');

  const recheck = useMutation({
    mutationFn: () => authApi.login(email, password),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['me'] });
      navigate('/home', { replace: true });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 403 && /consent/i.test(err.detail)) {
          setState({ kind: 'still-pending' });
          return;
        }
        if (err.status === 403) {
          setState({ kind: 'declined' });
          return;
        }
      }
      setState({ kind: 'invalid' });
    },
  });

  if (!email) {
    return (
      <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
        <h1 className="text-2xl font-semibold">Page expired</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          We need your email to recheck your account.
        </p>
        <p className="mt-4">
          <Link to="/signup" className="underline">Start over</Link>
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-semibold">Waiting for your parent to approve</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        We've emailed your parent at the address you provided. Once they click the approval link,
        you'll be able to log in.
      </p>

      {state.kind === 'idle' && (
        <Button className="mt-6 w-full" onClick={() => setState({ kind: 'recheck' })}>
          I've been approved
        </Button>
      )}

      {(state.kind === 'recheck' || state.kind === 'still-pending' || state.kind === 'invalid') && (
        <form
          className="mt-6 space-y-3"
          onSubmit={(e) => { e.preventDefault(); recheck.mutate(); }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="password">Enter your password to sign in</Label>
            <Input id="password" type="password" autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {state.kind === 'still-pending' && (
            <p role="alert" className="text-sm text-destructive">
              Not approved yet — please wait until your parent clicks the email link.
            </p>
          )}
          {state.kind === 'invalid' && (
            <p role="alert" className="text-sm text-destructive">
              Email or password incorrect.
            </p>
          )}
          <Button type="submit" disabled={recheck.isPending} className="w-full">
            {recheck.isPending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      )}

      {state.kind === 'declined' && (
        <div role="alert" className="mt-6 rounded-md border border-destructive/50 bg-destructive/5 p-4 text-destructive">
          <p className="font-semibold">Your parent has declined this account.</p>
          <p className="mt-2 text-sm">
            <Link to="/signup" className="underline">Try a different account</Link>.
          </p>
        </div>
      )}

      <p className="mt-6 text-sm text-muted-foreground">
        Wrong email? <Link to="/signup" className="underline">Use a different email</Link>.
      </p>
    </main>
  );
}
