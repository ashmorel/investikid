import { apiFetch } from './client';

export type PremiumRequestKind = 'module' | 'level' | 'challenge' | 'ticker' | 'coach';
export type PremiumRequestResult = { status: 'sent' | 'already_sent' | 'no_parent' };
export type ParentPremiumRequest = {
  id: string; child_username: string; context_kind: string;
  context_label: string; created_at: string;
};

export const premiumApi = {
  requestUnlock: (body: { kind: PremiumRequestKind; label: string }) =>
    apiFetch<PremiumRequestResult>('/premium/request', { method: 'POST', body: JSON.stringify(body) }),
  parentRequests: () => apiFetch<ParentPremiumRequest[]>('/parent/premium-requests'),
  declineRequest: (id: string) =>
    apiFetch<{ status: string }>(`/parent/premium-requests/${id}/decline`, { method: 'POST' }),
};
