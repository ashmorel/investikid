import { apiFetch } from './client';

export type SubscriptionStatus = {
  has_subscription: boolean;
  status: string | null;
  trial_ends_at: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};

export type Plan = 'annual' | 'monthly';

export type PlanOut = {
  plan: Plan;
  interval: 'year' | 'month';
  display_price: string;
  savings_pct: number | null;
  apple_product_id: string;
  google_product_id: string;
};

export type PlansResponse = { currency: string; plans: PlanOut[] };

export const billingApi = {
  createCheckout: (plan: Plan = 'annual') =>
    apiFetch<{ url: string }>('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan }),
    }),

  getPlans: () => apiFetch<PlansResponse>('/billing/plans'),

  createPortal: () =>
    apiFetch<{ url: string }>('/billing/portal', { method: 'POST' }),

  getStatus: () =>
    apiFetch<SubscriptionStatus>('/billing/status'),

  appleVerify: (jws: string) =>
    apiFetch<{ status: string }>('/billing/apple/verify',
      { method: 'POST', body: JSON.stringify({ jws }) }),

  appleAccountToken: () =>
    apiFetch<{ token: string }>('/billing/apple/account-token'),

  googleVerify: (body: { purchaseToken: string; productId: string }) =>
    apiFetch<{ status: string }>('/billing/google/verify',
      { method: 'POST', body: JSON.stringify(body) }),

  accountToken: () => apiFetch<{ token: string }>('/billing/account-token'),

  childAppleAccountToken: () =>
    apiFetch<{ token: string }>('/billing/child/apple/account-token'),

  childGoogleAccountToken: () =>
    apiFetch<{ token: string }>('/billing/child/account-token'),

  childPlans: () => apiFetch<PlansResponse>('/billing/child/plans'),

  childAppleVerify: (jws: string) =>
    apiFetch<{ status: string } | null>('/billing/child/apple/verify',
      { method: 'POST', body: JSON.stringify({ jws }) }),

  childGoogleVerify: (body: { purchaseToken: string; productId: string }) =>
    apiFetch<{ status: string } | null>('/billing/child/google/verify',
      { method: 'POST', body: JSON.stringify(body) }),
};
