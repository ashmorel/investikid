import { apiFetch } from './client';

export type Me = {
  id: string;
  email: string;
  username: string;
  dob: string;
  country_code: string;
  currency_code: string;
  topic_path: string | null;
  is_premium: boolean;
  parent_email: string | null;
  created_at: string;
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
};

export type RegisterResponse =
  | (Me & { status?: undefined })
  | { status: 'pending_consent'; user_id: string };

export const authApi = {
  me: () => apiFetch<Me>('/users/me'),
  login: (email: string, password: string) =>
    apiFetch<{ token_type: 'bearer' }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }),
  register: (body: RegisterBody) =>
    apiFetch<RegisterResponse>('/auth/register', {
      method: 'POST', body: JSON.stringify(body),
    }),
  logout: () => apiFetch<{ message: string }>('/auth/logout', { method: 'POST' }),
};
