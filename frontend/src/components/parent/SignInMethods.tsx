import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { parentAuthApi, type Provider } from '@/api/parentAuth';
import { parentApi } from '@/api/parent';
import { socialIdToken } from '@/lib/socialLogin';
import { addBioAccount, biometric, getBioAccounts, getDeviceId, removeBioAccount } from '@/lib/biometric';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

const PROVIDERS: { id: Provider; label: string }[] = [
  { id: 'apple', label: 'Apple' },
  { id: 'google', label: 'Google' },
];

// One parent per device, so a single fixed registry key is sufficient; the
// server exchange is keyed on device_id + secret, not on this key.
const PARENT_BIO_KEY = 'parent';

export function SignInMethods() {
  const { t } = useTranslation('parent');
  const qc = useQueryClient();
  const { data: identities = [], isLoading } = useQuery({
    queryKey: ['parent-identities'],
    queryFn: parentAuthApi.listIdentities,
  });
  const [pending, setPending] = useState<Provider | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [bioAvailable, setBioAvailable] = useState(false);
  const [bioOn, setBioOn] = useState(() => getBioAccounts().some((a) => a.key === PARENT_BIO_KEY));
  const [bioPending, setBioPending] = useState(false);
  useEffect(() => { void biometric.isAvailable().then(setBioAvailable); }, []);

  async function toggleBiometric(next: boolean) {
    setError(null);
    setBioPending(true);
    try {
      if (next) {
        if (!(await biometric.verify(t('signInMethods.biometric.enrollPrompt')))) return;
        const res = await parentApi.biometricEnroll(getDeviceId(), 'Parent');
        if (res?.secret) {
          await biometric.enroll(PARENT_BIO_KEY, 'Parent', res.secret);
          addBioAccount({ key: PARENT_BIO_KEY, label: 'Parent', kind: 'parent' });
          setBioOn(true);
        }
      } else {
        await parentApi.biometricUnenroll(getDeviceId());
        await biometric.clear(PARENT_BIO_KEY);
        removeBioAccount(PARENT_BIO_KEY);
        setBioOn(false);
      }
    } catch {
      setError(t('signInMethods.error.generic'));
    } finally {
      setBioPending(false);
    }
  }

  async function handleConnect(provider: Provider) {
    setError(null);
    setPending(provider);
    try {
      const { idToken, nonce } = await socialIdToken(provider);
      await parentAuthApi.linkProvider(provider, idToken, nonce);
      await qc.invalidateQueries({ queryKey: ['parent-identities'] });
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      if (status === 409) {
        setError(t('signInMethods.error.alreadyConnected'));
      } else {
        setError(t('signInMethods.error.generic'));
      }
    } finally {
      setPending(null);
    }
  }

  async function handleDisconnect(provider: Provider) {
    setError(null);
    setPending(provider);
    try {
      await parentAuthApi.unlinkProvider(provider);
      await qc.invalidateQueries({ queryKey: ['parent-identities'] });
    } catch {
      setError(t('signInMethods.error.generic'));
    } finally {
      setPending(null);
    }
  }

  return (
    <section
      className="mt-6 rounded-2xl border border-brand-100 bg-card px-4 py-4 shadow-sm sm:px-6"
      aria-label={t('signInMethods.sectionAriaLabel')}
    >
      <h2 className="mb-3 text-sm font-semibold text-brand-900">{t('signInMethods.heading')}</h2>

      {error && (
        <p role="alert" className="mb-3 rounded-lg bg-danger-50 px-3 py-2 text-sm text-danger-700">
          {error}
        </p>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">{t('signInMethods.loading')}</p>
      ) : (
        <ul className="space-y-2">
          {PROVIDERS.map(({ id, label }) => {
            const connected = (identities ?? []).some((i) => i.provider === id);
            const isPending = pending === id;
            return (
              <li key={id} className="flex items-center justify-between gap-4">
                <span className="text-sm font-medium">{label}</span>
                <div className="flex items-center gap-2">
                  {connected && (
                    <span className="text-xs text-muted-foreground">{t('signInMethods.connected')}</span>
                  )}
                  {connected ? (
                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={t('signInMethods.disconnectAriaLabel', { label })}
                      disabled={isPending}
                      onClick={() => handleDisconnect(id)}
                    >
                      {isPending ? t('signInMethods.disconnecting') : t('signInMethods.disconnect')}
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={t('signInMethods.connectAriaLabel', { label })}
                      disabled={isPending}
                      onClick={() => handleConnect(id)}
                    >
                      {isPending ? t('signInMethods.connecting') : t('signInMethods.connect')}
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {bioAvailable && (
        <div className="mt-3 border-t border-brand-100 pt-3">
          <div className="flex min-h-[44px] items-center justify-between gap-3">
            <Label htmlFor="parent-bio" className="text-sm font-medium">{t('signInMethods.faceIdLabel')}</Label>
            <Switch
              id="parent-bio"
              checked={bioOn}
              disabled={bioPending}
              onCheckedChange={(checked) => void toggleBiometric(checked)}
              aria-describedby="parent-bio-help"
            />
          </div>
          <p id="parent-bio-help" className="mt-1 text-xs text-muted-foreground">
            {t('signInMethods.faceIdHelp')}
          </p>
        </div>
      )}
    </section>
  );
}
