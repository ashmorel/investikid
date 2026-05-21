import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { parentApi } from '@/api/parent';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ParentLogin() {
  const [email, setEmail] = useState('');
  const [touched, setTouched] = useState(false);
  const valid = EMAIL_RE.test(email);
  const showError = touched && !valid;

  const submit = useMutation({
    mutationFn: () => parentApi.requestMagicLink(email),
  });

  if (submit.isSuccess) {
    return (
      <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
        <h1 className="text-2xl font-semibold">Check your inbox</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          If an Invest-Ed account is linked to {email}, we've sent a sign-in link.
          The link will expire in 15 minutes.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-semibold">Parent sign-in</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Enter the email address you used when your child signed up.
      </p>
      <form
        className="mt-6 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          setTouched(true);
          if (valid) submit.mutate();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email" type="email" autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={showError}
          />
          {showError && <p className="text-xs text-destructive">Enter a valid email address.</p>}
        </div>
        <Button type="submit" disabled={submit.isPending} className="w-full">
          {submit.isPending ? 'Sending…' : 'Send sign-in link'}
        </Button>
      </form>
    </main>
  );
}
