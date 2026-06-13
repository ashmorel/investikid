import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { App as CapacitorApp } from '@capacitor/app';
import { authApi } from '@/api/auth';
import { parentApi } from '@/api/parent';
import { biometric, getBioAccounts, getDeviceId, removeBioAccount, type BioAccount } from '@/lib/biometric';
import { Penny } from '@/components/child/ui/Penny';

const LOCK_TIMEOUT_MS = 120_000; // re-lock after >2 min backgrounded

type GateState = 'checking' | 'disabled' | 'locked' | 'unlocking' | 'unlocked';

/**
 * Wraps the app shell with a biometric lock (SP-Bio). Locks on cold launch and
 * after a >2-min background; tapping an enrolled account runs Face ID and, if
 * the persisted session has lapsed, silently re-mints via /biometric/exchange.
 * Disabled (renders children directly) on web, without hardware, or with no
 * enrolled accounts on this device.
 */
export function BiometricGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<GateState>('checking');
  const [accounts, setAccounts] = useState<BioAccount[]>([]);
  const [error, setError] = useState<string | null>(null);
  const backgroundedAt = useRef<number | null>(null);
  const navigate = useNavigate();

  // Initial determination: available + enrolled → locked, else disabled.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const list = getBioAccounts();
      if (list.length === 0 || !(await biometric.isAvailable())) {
        if (!cancelled) setState('disabled');
        return;
      }
      if (!cancelled) {
        setAccounts(list);
        setState('locked');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Background timeout → re-lock.
  useEffect(() => {
    if (state === 'disabled') return;
    const sub = CapacitorApp.addListener('appStateChange', ({ isActive }) => {
      if (!isActive) {
        backgroundedAt.current = Date.now();
      } else if (
        backgroundedAt.current !== null &&
        Date.now() - backgroundedAt.current > LOCK_TIMEOUT_MS
      ) {
        const list = getBioAccounts();
        if (list.length > 0) {
          setAccounts(list);
          setState('locked');
        }
      }
    });
    return () => { void sub.then((s) => s.remove()); };
  }, [state]);

  function forget(key: string, message: string) {
    removeBioAccount(key);
    const remaining = getBioAccounts();
    setAccounts(remaining);
    if (remaining.length === 0) { setState('disabled'); return; }
    setError(message);
    setState('locked');
  }

  async function unlock(acc: BioAccount) {
    setError(null);
    setState('unlocking');
    const r = await biometric.unlockRead(acc.key, 'Unlock InvestiKid');
    if (r.status === 'cancelled') { setState('locked'); return; }
    if (r.status === 'gone') {
      // secret invalidated locally (e.g. a new face/fingerprint was enrolled) → forget + password
      await biometric.clear(acc.key);
      forget(acc.key, 'Please sign in to set up Face ID again.');
      return;
    }
    try {
      const deviceId = getDeviceId();
      const res = acc.kind === 'parent'
        ? await parentApi.biometricExchange(deviceId, r.secret)
        : await authApi.biometricExchange(deviceId, r.secret);
      if (res?.secret) await biometric.enroll(acc.key, acc.label, res.secret);
      setState('unlocked');
    } catch {
      // dead server credential (revoked/expired/account gone) → forget it locally
      await biometric.clear(acc.key);
      forget(acc.key, "That didn't work — please sign in.");
    }
  }

  if (state === 'checking') return null;
  if (state === 'disabled' || state === 'unlocked') return <>{children}</>;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-brand-50 px-6">
      <Penny size={64} mood="happy" />
      <h1 className="text-xl font-extrabold text-brand-900">Welcome back</h1>
      <p aria-live="polite" className="sr-only">
        {state === 'unlocking' ? 'Checking Face ID' : 'Locked'}
      </p>
      <ul className="flex w-full max-w-xs flex-col gap-2" aria-label="Saved accounts">
        {accounts.map((acc) => (
          <li key={acc.key}>
            <button
              type="button"
              onClick={() => void unlock(acc)}
              disabled={state === 'unlocking'}
              className="flex min-h-[44px] w-full items-center justify-between rounded-xl border border-brand-200 bg-white px-4 text-sm font-bold text-brand-900 disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              <span>{acc.label}</span>
              <span aria-hidden="true">🔓</span>
            </button>
          </li>
        ))}
      </ul>
      {error && <p role="alert" className="text-sm font-semibold text-danger-700">{error}</p>}
      <button
        type="button"
        onClick={() => { setState('unlocked'); navigate('/login'); }}
        className="min-h-[44px] text-sm font-semibold text-brand-700 underline focus-visible:outline focus-visible:outline-2"
      >
        Sign in differently
      </button>
    </div>
  );
}
