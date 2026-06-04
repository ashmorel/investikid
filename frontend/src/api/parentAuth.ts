import { apiFetch } from './client';

export type Provider = 'apple' | 'google';
export type ParentIdentity = { provider: string; parent_email: string };

export const parentAuthApi = {
  oauthSignIn: (provider: Provider, idToken: string, nonce: string) =>
    apiFetch<{ status: string; email: string }>(`/parent/auth/oauth/${provider}`, {
      method: 'POST', body: JSON.stringify({ id_token: idToken, nonce }),
    }),
  linkProvider: (provider: Provider, idToken: string, nonce: string) =>
    apiFetch<{ status: string }>(`/parent/auth/oauth/${provider}/link`, {
      method: 'POST', body: JSON.stringify({ id_token: idToken, nonce }),
    }),
  unlinkProvider: (provider: Provider) =>
    apiFetch<{ status: string }>(`/parent/auth/oauth/${provider}/link`, { method: 'DELETE' }),
  listIdentities: () => apiFetch<ParentIdentity[]>('/parent/auth/identities'),
};
