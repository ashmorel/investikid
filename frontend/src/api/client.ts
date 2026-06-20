import { readCookie } from '@/lib/cookies';
import { isNativeApp } from '@/lib/platform';

// Native (Capacitor) builds load from the `capacitor://localhost` origin and
// have NO same-origin proxy, so they MUST call the backend at an absolute URL.
// The web build leaves this empty and relies on same-origin + Vercel rewrites.
// A native build with an unset VITE_API_BASE_URL would otherwise bake an empty
// base, fetch `capacitor://localhost/...`, fail every call, and render a blank
// screen — so native falls back to the production backend. Override the env var
// to point a native build at testing/staging instead.
const NATIVE_API_FALLBACK = 'https://investikid.up.railway.app';

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || (isNativeApp() ? NATIVE_API_FALLBACK : '');

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
    public context?: unknown,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

// Paths that must never trigger a refresh attempt (they ARE the auth surface).
// A 401 from /auth/refresh itself, or from login/register, is a real failure —
// refreshing would loop or mask a genuine bad-credentials response.
const AUTH_PATHS = ['/auth/refresh', '/auth/login', '/auth/register'];
function isAuthPath(path: string): boolean {
  return AUTH_PATHS.some((p) => path.startsWith(p));
}

function buildHeaders(method: string, extra?: HeadersInit): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((extra as Record<string, string>) ?? {}),
  };
  if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
    const csrf = readCookie('csrf_token');
    if (csrf) headers['X-CSRF-Token'] = csrf;
    // Native (Capacitor) requests can't read the cross-domain csrf cookie to
    // echo it. This header identifies first-party native traffic for the
    // backend's CSRF check; browsers cannot add it cross-site without a CORS
    // preflight (which the server denies for untrusted origins).
    if (isNativeApp()) headers['X-Capacitor-App'] = '1';
  }
  return headers;
}

// Single-flight token refresh: concurrent 401s share one /auth/refresh call so
// we don't fire N parallel refreshes (which would race the rotating refresh
// token). Resets once settled so a later 401 can refresh again.
let refreshInFlight: Promise<boolean> | null = null;
function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: buildHeaders('POST'),
        });
        return res.ok;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit,
): Promise<T | null> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const doFetch = () =>
    fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      ...init,
      method,
      headers: buildHeaders(method, init?.headers),
    });

  let res = await doFetch();
  // Silent session refresh: on a 401 for a non-auth path, refresh the access
  // token once (single-flight) and retry. Entitlement is still checked
  // server-side per request, so a longer session never grants premium.
  if (res.status === 401 && !isAuthPath(path)) {
    const refreshed = await refreshSession();
    if (refreshed) res = await doFetch();
  }

  if (!res.ok) {
    let detail = res.statusText;
    let code: string | undefined;
    let context: unknown;
    try {
      const body = await res.json();
      const d = body?.detail;
      if (typeof d === 'string') {
        detail = d;
      } else if (d && typeof d === 'object') {
        if (typeof d.message === 'string') detail = d.message;
        if (typeof d.code === 'string') code = d.code;
        context = d.context;
      }
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail, code, context);
  }
  if (res.status === 204) return null;
  return (await res.json()) as T;
}
