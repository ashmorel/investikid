import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { parentApi } from '@/api/parent';
import { parentAuthApi } from '@/api/parentAuth';
import { socialIdToken } from '@/lib/socialLogin';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ParentLogin() {
  const { t } = useTranslation('auth');
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [touched, setTouched] = useState(false);
  const [socialError, setSocialError] = useState<string | null>(null);
  const [socialPending, setSocialPending] = useState<'apple' | 'google' | null>(null);
  const valid = EMAIL_RE.test(email);
  const showError = touched && !valid;

  const submit = useMutation({
    mutationFn: () => parentApi.requestMagicLink(email),
  });

  async function handleSocial(provider: 'apple' | 'google') {
    setSocialError(null);
    setSocialPending(provider);
    try {
      const { idToken, nonce } = await socialIdToken(provider);
      await parentAuthApi.oauthSignIn(provider, idToken, nonce);
      navigate('/parent');
    } catch {
      setSocialError(t('parentLogin.socialError'));
    } finally {
      setSocialPending(null);
    }
  }

  if (submit.isSuccess) {
    return (
      <AuthPage title={t('parentLogin.success.title')}>
        <p className="text-sm text-muted-foreground">
          {t('parentLogin.success.message', { email })}
        </p>
      </AuthPage>
    );
  }

  return (
    <AuthPage title={t('parentLogin.title')} subtitle={t('parentLogin.subtitle')}>
      <p className="text-sm text-muted-foreground">
        {t('parentLogin.intro')}
      </p>

      {/* Social login buttons */}
      <div className="mt-6 space-y-3">
        <Button
          type="button"
          variant="outline"
          className="w-full text-base"
          disabled={socialPending !== null}
          onClick={() => handleSocial('apple')}
        >
          {socialPending === 'apple' ? t('parentLogin.signingIn') : t('parentLogin.continueWithApple')}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="w-full text-base"
          disabled={socialPending !== null}
          onClick={() => handleSocial('google')}
        >
          {socialPending === 'google' ? t('parentLogin.signingIn') : t('parentLogin.continueWithGoogle')}
        </Button>
      </div>

      {socialError && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {socialError}
        </p>
      )}

      {/* Divider */}
      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-border" aria-hidden="true" />
        <span className="text-xs text-muted-foreground">{t('parentLogin.or')}</span>
        <div className="h-px flex-1 bg-border" aria-hidden="true" />
      </div>

      {/* Magic-link form */}
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          setTouched(true);
          if (valid) submit.mutate();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">{t('parentLogin.email')}</Label>
          <Input
            id="email" type="email" autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={showError}
          />
          {showError && <p className="text-xs text-destructive">{t('parentLogin.emailError')}</p>}
        </div>
        <Button type="submit" disabled={submit.isPending} className="w-full">
          {submit.isPending ? t('parentLogin.sending') : t('parentLogin.sendSignInLink')}
        </Button>
      </form>
    </AuthPage>
  );
}
