import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi } from '@/api/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

export default function ForgotPassword() {
  const { t } = useTranslation('auth');
  const [identifier, setIdentifier] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const submit = useMutation({
    mutationFn: () => authApi.forgotPassword(identifier),
    onSuccess: () => setSubmitted(true),
    onError: () => setSubmitted(true), // always show neutral confirmation
  });

  if (submitted) {
    return (
      <AuthPage title={t('forgotPassword.success.title')}>
        <p className="text-sm text-muted-foreground">
          {t('forgotPassword.success.message')}
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          <Link to="/login" className="underline">{t('forgotPassword.success.backToSignIn')}</Link>
        </p>
      </AuthPage>
    );
  }

  return (
    <AuthPage title={t('forgotPassword.title')} subtitle={t('forgotPassword.subtitle')}>
      <p className="text-sm text-muted-foreground">
        {t('forgotPassword.intro')}
      </p>
      <form
        className="mt-6 space-y-3"
        onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="identifier">{t('forgotPassword.identifierLabel')}</Label>
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
          {submit.isPending ? t('forgotPassword.sending') : t('forgotPassword.sendResetLink')}
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        <Link to="/login" className="underline">{t('forgotPassword.backToSignIn')}</Link>
      </p>
    </AuthPage>
  );
}
