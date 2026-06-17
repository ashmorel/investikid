import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi } from '@/api/auth';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthPage } from '@/components/AuthPage';

type State =
  | { kind: 'idle' }
  | { kind: 'recheck' }
  | { kind: 'still-pending' }
  | { kind: 'declined' }
  | { kind: 'invalid' };

export default function PendingConsent() {
  const { t } = useTranslation('auth');
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
      <AuthPage title={t('pendingConsent.expiredTitle')} subtitle={t('pendingConsent.expiredSubtitle')}>
        <p className="text-sm text-muted-foreground">
          {t('pendingConsent.expiredBody')}
        </p>
        <p className="mt-4">
          <Link to="/signup" className="underline">{t('pendingConsent.startOver')}</Link>
        </p>
      </AuthPage>
    );
  }

  return (
    <AuthPage title={t('pendingConsent.almostThereTitle')} subtitle={t('pendingConsent.almostThereSubtitle')}>
      <p className="text-sm text-muted-foreground">
        {t('pendingConsent.body')}
      </p>

      {state.kind === 'idle' && (
        <Button className="mt-6 w-full" onClick={() => setState({ kind: 'recheck' })}>
          {t('pendingConsent.iHaveBeenApproved')}
        </Button>
      )}

      {(state.kind === 'recheck' || state.kind === 'still-pending' || state.kind === 'invalid') && (
        <form
          className="mt-6 space-y-3"
          onSubmit={(e) => { e.preventDefault(); recheck.mutate(); }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="password">{t('pendingConsent.enterPassword')}</Label>
            <Input id="password" type="password" autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {state.kind === 'still-pending' && (
            <p role="alert" className="text-sm text-destructive">
              {t('pendingConsent.stillPending')}
            </p>
          )}
          {state.kind === 'invalid' && (
            <p role="alert" className="text-sm text-destructive">
              {t('pendingConsent.invalid')}
            </p>
          )}
          <Button type="submit" disabled={recheck.isPending} className="w-full">
            {recheck.isPending ? t('pendingConsent.signingIn') : t('pendingConsent.signIn')}
          </Button>
        </form>
      )}

      {state.kind === 'declined' && (
        <div role="alert" className="mt-6 rounded-md border border-destructive/50 bg-destructive/5 p-4 text-destructive">
          <p className="font-semibold">{t('pendingConsent.declined')}</p>
          <p className="mt-2 text-sm">
            <Link to="/signup" className="underline">{t('pendingConsent.tryDifferent')}</Link>.
          </p>
        </div>
      )}

      <p className="mt-6 text-sm text-muted-foreground">
        {t('pendingConsent.wrongEmail')} <Link to="/signup" className="underline">{t('pendingConsent.useDifferent')}</Link>.
      </p>
    </AuthPage>
  );
}
