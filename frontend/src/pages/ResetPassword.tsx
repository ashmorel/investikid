import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

function validatePassword(pw: string): string | null {
  if (pw.length < 12) return 'Password must be at least 12 characters.';
  if (!/[a-zA-Z]/.test(pw)) return 'Password must contain at least one letter.';
  if (!/[0-9]/.test(pw)) return 'Password must contain at least one digit.';
  return null;
}

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [clientError, setClientError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [expired, setExpired] = useState(false);

  const submit = useMutation({
    mutationFn: () => authApi.resetPassword(token, newPassword),
    onSuccess: () => setSuccess(true),
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 410) {
          setExpired(true);
          return;
        }
        if (err.status === 422) {
          setServerError(err.detail);
          return;
        }
        setServerError(err.detail || 'Something went wrong. Please try again.');
        return;
      }
      setServerError('Something went wrong. Please try again.');
    },
  });

  if (!token) {
    return (
      <AuthPage title="That link didn't work" subtitle="Please use the reset link from your email.">
        <p role="alert" className="text-sm text-destructive">
          Invalid link. Please use the reset link from your email.
        </p>
      </AuthPage>
    );
  }

  if (success) {
    return (
      <AuthPage title="Password updated">
        <p className="text-sm text-muted-foreground">
          Your password has been reset successfully.
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          <Link to="/login" className="underline">Sign in with your new password</Link>
        </p>
      </AuthPage>
    );
  }

  if (expired) {
    return (
      <AuthPage title="Link expired" subtitle="Request a fresh reset link when you're ready.">
        <p className="text-sm text-muted-foreground">
          This link has expired or was already used. Request a new one.
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          <Link to="/forgot-password" className="underline">Request a new reset link</Link>
        </p>
      </AuthPage>
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setClientError(null);
    setServerError(null);
    const pwErr = validatePassword(newPassword);
    if (pwErr) { setClientError(pwErr); return; }
    if (newPassword !== confirm) { setClientError('Passwords do not match.'); return; }
    submit.mutate();
  }

  return (
    <AuthPage title="Choose a new password">
      <form className="space-y-3" onSubmit={handleSubmit}>
        <div className="space-y-1.5">
          <Label htmlFor="new-password">New password</Label>
          <Input
            id="new-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Min 12 characters, must include a letter and a digit.
          </p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirm-password">Confirm new password</Label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="off"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </div>
        {clientError && (
          <p role="alert" className="text-sm text-destructive">{clientError}</p>
        )}
        {serverError && (
          <p role="alert" className="text-sm text-destructive">{serverError}</p>
        )}
        <Button type="submit" disabled={submit.isPending} className="w-full">
          {submit.isPending ? 'Updating…' : 'Update password'}
        </Button>
      </form>
    </AuthPage>
  );
}
