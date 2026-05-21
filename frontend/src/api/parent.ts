import { apiFetch } from './client';

export type Child = {
  user_id: string;
  username: string;
  country_code: string;
  is_active: boolean;
  is_premium: boolean;
  parent_consent_given_at: string | null;
  consent_declined_at: string | null;
  deleted_at: string | null;
  deletion_requested_at: string | null;
};

export const parentApi = {
  requestMagicLink: (email: string) =>
    apiFetch<{ status: string }>('/parent/auth/request', {
      method: 'POST', body: JSON.stringify({ email }),
    }),
  magicCallback: (token: string) =>
    apiFetch<{ status: string; email: string }>(
      `/parent/auth/callback?token=${encodeURIComponent(token)}`,
    ),
  logout: () => apiFetch<{ status: string }>('/parent/auth/logout', { method: 'POST' }),
  listChildren: () => apiFetch<Child[]>('/parent/children'),
  freezeChild: (userId: string, frozen: boolean) =>
    apiFetch<{ status: string; frozen: boolean }>(
      `/parent/children/${userId}/freeze`,
      { method: 'POST', body: JSON.stringify({ frozen }) },
    ),
  eraseChild: (userId: string) =>
    apiFetch<{ status: string }>(
      `/parent/children/${userId}/erasure`,
      { method: 'POST' },
    ),
};
