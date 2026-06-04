import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { parentAuthApi, type Provider } from '@/api/parentAuth';
import { socialIdToken } from '@/lib/socialLogin';
import { Button } from '@/components/ui/button';

const PROVIDERS: { id: Provider; label: string }[] = [
  { id: 'apple', label: 'Apple' },
  { id: 'google', label: 'Google' },
];

export function SignInMethods() {
  const qc = useQueryClient();
  const { data: identities = [], isLoading } = useQuery({
    queryKey: ['parent-identities'],
    queryFn: parentAuthApi.listIdentities,
  });
  const [pending, setPending] = useState<Provider | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        setError('That account is already connected to a different parent.');
      } else {
        setError('Something went wrong. Please try again.');
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
      setError('Something went wrong. Please try again.');
    } finally {
      setPending(null);
    }
  }

  return (
    <section
      className="mt-6 rounded-2xl border border-brand-100 bg-card px-4 py-4 shadow-sm sm:px-6"
      aria-label="Sign-in methods"
    >
      <h2 className="mb-3 text-sm font-semibold text-brand-900">Sign-in methods</h2>

      {error && (
        <p role="alert" className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
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
                    <span className="text-xs text-muted-foreground">Connected</span>
                  )}
                  {connected ? (
                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={`Disconnect ${label}`}
                      disabled={isPending}
                      onClick={() => handleDisconnect(id)}
                    >
                      {isPending ? 'Disconnecting…' : 'Disconnect'}
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={`Connect ${label}`}
                      disabled={isPending}
                      onClick={() => handleConnect(id)}
                    >
                      {isPending ? 'Connecting…' : 'Connect'}
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
