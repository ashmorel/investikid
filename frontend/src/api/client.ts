import { readCookie } from '@/lib/cookies';
import { isNativeApp } from '@/lib/platform';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

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

export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit,
): Promise<T | null> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init?.headers as Record<string, string>) ?? {}),
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
  const res = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init, method, headers });
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
