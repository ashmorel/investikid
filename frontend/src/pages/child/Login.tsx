import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi, type Me } from '@/api/auth';
import { ApiError } from '@/api/client';
import { isNativeApp } from '@/lib/platform';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

// After /auth/login, confirm the auth cookie is actually usable by polling /me.
// On iOS WKWebView the cross-domain Set-Cookie can lag the next request, so the
// first /me 401s; poll for ~2s to let it settle. Returns the user, or null.
async function establishSession(): Promise<Me | null> {
  for (let i = 0; i < 8; i++) {
    try {
      const me = await authApi.me();
      if (me) return me;
    } catch {
      /* cookie not ready yet — retry */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  return null;
}

export default function Login() {
  const { t } = useTranslation('auth');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const submit = useMutation({
    mutationFn: () => authApi.login(email, password),
    onSuccess: async () => {
      let me = await establishSession();
      if (!me && isNativeApp()) {
        // iOS cold-start cookie race: the first login's cookie didn't persist.
        // Re-issue the login (the manual "try again" that works) and re-verify.
        try {
          await authApi.login(email, password);
        } catch {
          /* fall through to the error path below */
        }
        me = await establishSession();
      }
      if (me) {
        qc.setQueryData(['me'], me);
        navigate('/home', { replace: true });
      } else {
        setError(t('login.error.sessionFailed'));
      }
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 403 && /consent/i.test(err.detail)) {
          navigate(`/pending-consent?email=${encodeURIComponent(email)}`, { replace: true });
          return;
        }
        if (err.status === 403) {
          setError(t('login.error.accountDenied'));
          return;
        }
        setError(t('login.error.wrongCredentials'));
        return;
      }
      setError(t('login.error.generic'));
    },
  });

  return (
    <AuthPage title={t('login.title')} subtitle={t('login.subtitle')}>
      <form
        className="space-y-3"
        onSubmit={(e) => { e.preventDefault(); setError(null); submit.mutate(); }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">{t('login.fields.email')}</Label>
          <Input id="email" type="email" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">{t('login.fields.password')}</Label>
          <Input id="password" type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <Button type="submit" disabled={submit.isPending} className="w-full">
          {submit.isPending ? t('login.signingIn') : t('login.signIn')}
        </Button>
      </form>
      <p className="mt-4 text-sm text-muted-foreground">
        <Link to="/forgot-password" className="underline">{t('login.forgotPassword')}</Link>
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        {t('login.newToApp')} <Link to="/signup" className="underline">{t('login.createAccount')}</Link>.
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        {t('login.curious')} <Link to="/try" className="underline">{t('login.tryLesson')}</Link>{t('login.tryLessonSuffix')}
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        {t('login.areYouParent')} <Link to="/parent/login" className="font-medium text-brand-700 underline">{t('login.manageChild')}</Link>
      </p>
    </AuthPage>
  );
}
