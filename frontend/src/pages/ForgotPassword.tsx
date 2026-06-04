import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

export default function ForgotPassword() {
  const [identifier, setIdentifier] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const submit = useMutation({
    mutationFn: () => authApi.forgotPassword(identifier),
    onSuccess: () => setSubmitted(true),
    onError: () => setSubmitted(true), // always show neutral confirmation
  });

  if (submitted) {
    return (
      <AuthPage title="Check your email">
        <p className="text-sm text-muted-foreground">
          If that account exists, we've sent a reset link. Check your email (or ask a grown-up).
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          <Link to="/login" className="underline">Back to sign in</Link>
        </p>
      </AuthPage>
    );
  }

  return (
    <AuthPage title="Forgot your password?" subtitle="We'll email you a reset link.">
      <p className="text-sm text-muted-foreground">
        Enter your email or username and we'll send you a reset link.
      </p>
      <form
        className="mt-6 space-y-3"
        onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="identifier">Email or username</Label>
          <Input
            id="identifier"
            type="text"
            autoComplete="email"
            required
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={submit.isPending} className="w-full">
          {submit.isPending ? 'Sending…' : 'Send reset link'}
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        <Link to="/login" className="underline">Back to sign in</Link>
      </p>
    </AuthPage>
  );
}
