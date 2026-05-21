import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const submit = useMutation({
    mutationFn: () => authApi.login(email, password),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['me'] });
      navigate('/home', { replace: true });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 403 && /consent/i.test(err.detail)) {
          navigate(`/pending-consent?email=${encodeURIComponent(email)}`, { replace: true });
          return;
        }
        if (err.status === 403) {
          setError('Account access denied. Please contact your parent.');
          return;
        }
        setError('Email or password incorrect.');
        return;
      }
      setError('Something went wrong. Please try again.');
    },
  });

  return (
    <main className="mx-auto max-w-md px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-semibold">Sign in to Invest-Ed</h1>
      <form
        className="mt-6 space-y-3"
        onSubmit={(e) => { e.preventDefault(); setError(null); submit.mutate(); }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <Button type="submit" disabled={submit.isPending} className="w-full">
          {submit.isPending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
      <p className="mt-4 text-sm text-muted-foreground">
        <Link to="/forgot-password" className="underline">Forgot password?</Link>
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        New to Invest-Ed? <Link to="/signup" className="underline">Create an account</Link>.
      </p>
    </main>
  );
}
