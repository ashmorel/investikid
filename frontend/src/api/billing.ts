import { apiFetch } from './client';

export type SubscriptionStatus = {
  has_subscription: boolean;
  status: string | null;
  trial_ends_at: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};

export const billingApi = {
  createCheckout: () =>
    apiFetch<{ url: string }>('/billing/checkout', { method: 'POST' }),

  createPortal: () =>
    apiFetch<{ url: string }>('/billing/portal', { method: 'POST' }),

  getStatus: () =>
    apiFetch<SubscriptionStatus>('/billing/status'),

  appleVerify: (jws: string) =>
    apiFetch<{ status: string }>('/billing/apple/verify',
      { method: 'POST', body: JSON.stringify({ jws }) }),

  appleAccountToken: () =>
    apiFetch<{ token: string }>('/billing/apple/account-token'),
};
