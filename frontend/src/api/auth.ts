import { apiFetch } from './client';

// Must stay in sync with backend settings.privacy_notice_version.
// No FE/BE shared config endpoint yet — update both sides when the version changes.
export const PRIVACY_NOTICE_VERSION = '2026-05-16';

export type Me = {
  id: string;
  email: string;
  username: string;
  dob: string;
  country_code: string;
  currency_code: string;
  topic_path: string | null;
  content_region: string | null;
  is_premium: boolean;
  push_enabled?: boolean;
  is_admin: boolean;
  age_tier: 'explorer' | 'investor';
  parent_email: string | null;
  created_at: string;
  email_verified_at: string | null;
};

export type RegisterBody = {
  email: string;
  username: string;
  password: string;
  dob: string;            // YYYY-MM-DD
  country_code: string;
  currency_code: string;
  parent_email?: string | null;
  topic_path?: string | null;
  policy_version_accepted?: string;
};

export type RegisterResponse =
  | (Me & { status?: undefined })
  | { status: 'pending_consent'; user_id: string };

export const authApi = {
  me: () => apiFetch<Me>('/users/me'),
  updatePreferences: (body: {
    topic_path?: string | null;
    content_region?: string | null;
    currency_code?: string | null;
  }) =>
    apiFetch<Me>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  login: (email: string, password: string) =>
    apiFetch<{ token_type: 'bearer' }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }),
  register: (body: RegisterBody) =>
    apiFetch<RegisterResponse>('/auth/register', {
      method: 'POST', body: JSON.stringify(body),
    }),
  logout: () => apiFetch<{ message: string }>('/auth/logout', { method: 'POST' }),
  forgotPassword: (email: string) =>
    apiFetch<{ status: string }>('/auth/forgot-password', {
      method: 'POST', body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, new_password: string) =>
    apiFetch<{ status: string }>('/auth/reset-password', {
      method: 'POST', body: JSON.stringify({ token, new_password }),
    }),
  verifyEmail: (token: string) =>
    apiFetch<{ status: string }>(`/auth/verify-email?token=${encodeURIComponent(token)}`),
  resendVerifyEmail: () =>
    apiFetch<{ status: string }>('/auth/verify-email/resend', { method: 'POST' }),
};
