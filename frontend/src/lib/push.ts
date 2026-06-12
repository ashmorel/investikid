// Server-push registration (M7). Double-gated consent:
//   1. parent master switch (me.push_enabled, set in the parent dashboard)
//   2. the child's in-app toggle (the caller invokes enablePush only then)
// Web is always a no-op; the Capacitor plugin is imported dynamically so web
// bundles never load it. Until the iOS Push capability + Firebase are set up
// (operator steps), registration simply never produces a token — harmless.
import { apiFetch } from '@/api/client';
import { isAndroid, isNativeApp } from '@/lib/platform';

const TOKEN_KEY = 'push-device-token';

export type PushEnableResult = 'registered' | 'permission-denied' | 'unavailable';

export async function enablePush(parentEnabled: boolean): Promise<PushEnableResult> {
  if (!isNativeApp() || !parentEnabled) return 'unavailable';
  try {
    const { PushNotifications } = await import('@capacitor/push-notifications');
    let status = await PushNotifications.checkPermissions();
    if (status.receive === 'prompt') {
      status = await PushNotifications.requestPermissions();
    }
    if (status.receive !== 'granted') return 'permission-denied';

    return await new Promise<PushEnableResult>((resolve) => {
      void PushNotifications.addListener('registration', (token) => {
        void apiFetch('/users/me/push-devices', {
          method: 'POST',
          body: JSON.stringify({ platform: isAndroid() ? 'android' : 'ios', token: token.value }),
        })
          .then(() => {
            localStorage.setItem(TOKEN_KEY, token.value);
            resolve('registered');
          })
          .catch(() => resolve('unavailable'));
      });
      void PushNotifications.addListener('registrationError', () => resolve('unavailable'));
      void PushNotifications.register();
    });
  } catch {
    return 'unavailable';
  }
}

export async function disablePush(): Promise<void> {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    localStorage.removeItem(TOKEN_KEY);
    try {
      await apiFetch(`/users/me/push-devices/${encodeURIComponent(token)}`, { method: 'DELETE' });
    } catch {
      // best-effort — the server prunes dead tokens anyway
    }
  }
}

export function isPushRegistered(): boolean {
  return localStorage.getItem(TOKEN_KEY) !== null;
}
