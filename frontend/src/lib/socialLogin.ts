import { SocialLogin } from '@capgo/capacitor-social-login';
import { makeNonce } from './nonce';
import type { Provider } from '@/api/parentAuth';

let initialized = false;

async function ensureInit(): Promise<void> {
  if (initialized) return;
  // Public client IDs only (no secrets). Provided via VITE_* env at build time.
  await SocialLogin.initialize({
    google: {
      webClientId: import.meta.env.VITE_GOOGLE_WEB_CLIENT_ID,
      iOSClientId: import.meta.env.VITE_GOOGLE_IOS_CLIENT_ID,
    },
    apple: {
      clientId: import.meta.env.VITE_APPLE_SERVICES_ID,
      // Deterministic web redirect so it always equals the Apple Services ID
      // "Return URL" exactly (the plugin otherwise defaults to window.location.href,
      // which can pick up query strings and cause redirect_uri mismatches).
      // Native iOS sign-in ignores this. Register this exact URL in Apple.
      redirectUrl: `${window.location.origin}/parent/login`,
    },
  });
  initialized = true;
}

// Returns the provider ID token + the nonce used; caller posts both to the backend.
export async function socialIdToken(
  provider: Provider,
): Promise<{ idToken: string; nonce: string }> {
  await ensureInit();
  const nonce = makeNonce();
  const res = await SocialLogin.login({
    provider,
    options: { nonce },
  });
  // Both Google (GoogleLoginResponseOnline) and Apple (AppleProviderResponse)
  // surface idToken at res.result.idToken
  const idToken = (res as { result?: { idToken?: string | null } }).result?.idToken;
  if (!idToken) throw new Error('No ID token from provider');
  return { idToken, nonce };
}
