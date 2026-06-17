import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

function validatePassword(pw: string, t: (k: string) => string): string | null {
  if (pw.length < 12) return t('resetPassword.error.minLength');
  if (!/[a-zA-Z]/.test(pw)) return t('resetPassword.error.needsLetter');
  if (!/[0-9]/.test(pw)) return t('resetPassword.error.needsDigit');
  return null;
}

export default function ResetPassword() {
  const { t } = useTranslation('auth');
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
        setServerError(err.detail || t('resetPassword.error.generic'));
        return;
      }
      setServerError(t('resetPassword.error.generic'));
    },
  });

  if (!token) {
    return (
      <AuthPage title={t('resetPassword.invalidLink.title')} subtitle={t('resetPassword.invalidLink.subtitle')}>
        <p role="alert" className="text-sm text-destructive">
          {t('resetPassword.invalidLink.message')}
        </p>
      </AuthPage>
    );
  }

  if (success) {
    return (
      <AuthPage title={t('resetPassword.success.title')}>
        <p className="text-sm text-muted-foreground">
          {t('resetPassword.success.message')}
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          <Link to="/login" className="underline">{t('resetPassword.success.signInLink')}</Link>
        </p>
      </AuthPage>
    );
  }

  if (expired) {
    return (
      <AuthPage title={t('resetPassword.expired.title')} subtitle={t('resetPassword.expired.subtitle')}>
        <p className="text-sm text-muted-foreground">
          {t('resetPassword.expired.message')}
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          <Link to="/forgot-password" className="underline">{t('resetPassword.expired.requestLink')}</Link>
        </p>
      </AuthPage>
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setClientError(null);
    setServerError(null);
    const pwErr = validatePassword(newPassword, t);
    if (pwErr) { setClientError(pwErr); return; }
    if (newPassword !== confirm) { setClientError(t('resetPassword.error.mismatch')); return; }
    submit.mutate();
  }

  return (
    <AuthPage title={t('resetPassword.title')}>
      <form className="space-y-3" onSubmit={handleSubmit}>
        <div className="space-y-1.5">
          <Label htmlFor="new-password">{t('resetPassword.newPassword')}</Label>
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
            {t('resetPassword.newPasswordHint')}
          </p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirm-password">{t('resetPassword.confirmPassword')}</Label>
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
          {submit.isPending ? t('resetPassword.updating') : t('resetPassword.updatePassword')}
        </Button>
      </form>
    </AuthPage>
  );
}
